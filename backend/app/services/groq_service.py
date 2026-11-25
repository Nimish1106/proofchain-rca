import json
import logging
import time
from functools import lru_cache

from groq import APIError, APIStatusError, Groq

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AIConfigurationError(Exception):
    """Raised when AI configuration is incomplete."""


class AIConnectionError(Exception):
    """Raised when the configured AI service is unavailable."""


class AIModelUnavailableError(Exception):
    """Raised when the requested model is unavailable."""


class StructuredOutputError(Exception):
    """Raised when a model response cannot be decoded."""


@lru_cache(maxsize=1)
def get_groq_client() -> Groq:
    """
    Create one reusable Groq SDK client.
    Credentials and request settings come from configuration.
    """
    settings = get_settings()
    if not settings.groq_api_key:
        raise AIConfigurationError(
            "GROQ_API_KEY is not configured."
        )
    if not settings.groq_model:
        raise AIConfigurationError(
            "GROQ_MODEL is not configured."
        )
    return Groq(
        api_key=settings.groq_api_key.get_secret_value(),
        timeout=settings.groq_timeout_seconds,
        max_retries=settings.groq_max_retries,
    )


def get_configured_model() -> str:
    """Return the configured Groq model identifier."""
    settings = get_settings()
    if not settings.groq_model:
        raise AIConfigurationError(
            "GROQ_MODEL is not configured."
        )
    return settings.groq_model


def verify_groq_connection() -> dict:
    """
    Verify API authentication and configured model access.
    Uses the model-list endpoint rather than generating
    unnecessary tokens.
    """
    client = get_groq_client()
    selected_model = get_configured_model()
    try:
        response = client.models.list()
        available_models = {
            model.id for model in response.data
        }
    except APIError as exc:
        raise AIConnectionError(
            "Unable to communicate with Groq. "
            "Check API credentials, network connectivity "
            "and account permissions."
        ) from exc

    if selected_model not in available_models:
        raise AIModelUnavailableError(
            "The configured model is not available "
            "to this Groq account."
        )

    return {
        "connected": True,
        "model": selected_model,
        "available_model_count": len(available_models),
    }


def generate_structured_response(
    *,
    messages: list[dict[str, str]],
    schema_name: str,
    json_schema: dict,
) -> dict:
    """
    Request a strict JSON Schema response from Groq.
    The configured model must support Groq strict structured outputs.
    Pydantic validation will be applied separately by the calling
    application service.
    """
    client = get_groq_client()
    selected_model = get_configured_model()
    max_rate_limit_retries = 2

    response = None
    use_json_object_fallback = False

    for attempt in range(max_rate_limit_retries + 2):
        request_messages = messages
        if use_json_object_fallback:
            schema_note = (
                "\n\nReturn ONLY a valid JSON object strictly conforming to this JSON Schema "
                "(no markdown, no extra keys):\n"
                + json.dumps(json_schema, separators=(",", ":"))
            )
            request_messages = [
                {
                    "role": msg["role"],
                    "content": (
                        msg["content"] + schema_note
                        if idx == 0 and msg["role"] == "system"
                        else msg["content"]
                    ),
                }
                for idx, msg in enumerate(messages)
            ]
            response_format = {"type": "json_object"}
        else:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": json_schema,
                },
            }

        try:
            response = client.chat.completions.create(
                model=selected_model,
                messages=request_messages,
                temperature=0,
                max_completion_tokens=4500,
                response_format=response_format,
            )
            break
        except APIStatusError as exc:
            if (
                exc.status_code == 400
                and not use_json_object_fallback
                and "json_validate_failed" in str(exc)
            ):
                logger.warning(
                    "Groq strict json_schema validation glitched on %s; retrying with json_object.",
                    schema_name,
                )
                use_json_object_fallback = True
                continue

            headers = getattr(exc.response, "headers", {}) or {}
            retry_after_raw = headers.get("retry-after")
            remaining_tokens_raw = headers.get(
                "x-ratelimit-remaining-tokens"
            )
            limit_tokens_raw = headers.get("x-ratelimit-limit-tokens")

            is_tpm_block = exc.status_code in (413, 429) and (
                "rate_limit_exceeded" in str(exc)
                or retry_after_raw is not None
            )

            # Retry only if the TPM bucket was partially consumed by an earlier
            # step (not when a single prompt itself exceeds the entire TPM limit).
            bucket_partially_used = (
                remaining_tokens_raw is not None
                and limit_tokens_raw is not None
                and int(remaining_tokens_raw) < int(limit_tokens_raw)
            )
            if (
                is_tpm_block
                and attempt < max_rate_limit_retries
                and (bucket_partially_used or exc.status_code == 429)
            ):
                wait_seconds = 10.0
                if retry_after_raw is not None:
                    try:
                        wait_seconds = min(
                            max(float(retry_after_raw) + 1.0, 1.0), 65.0
                        )
                    except ValueError:
                        wait_seconds = 10.0
                logger.warning(
                    "Groq TPM rate limit on %s (status=%s); waiting %.1fs before retry.",
                    schema_name,
                    exc.status_code,
                    wait_seconds,
                )
                time.sleep(wait_seconds)
                continue

            if is_tpm_block:
                raise AIConnectionError(
                    "Groq token rate limit (TPM) exceeded for this request. "
                    "Reduce evidence volume or retry shortly."
                ) from exc

            raise AIConnectionError(
                "Groq structured generation failed."
            ) from exc
        except APIError as exc:
            raise AIConnectionError(
                "Groq structured generation failed."
            ) from exc

    assert response is not None

    if not response.choices:
        raise StructuredOutputError(
            "Groq returned no response choices."
        )

    message = response.choices[0].message
    if getattr(message, "refusal", None):
        raise StructuredOutputError(
            "The AI model refused the request."
        )

    content = message.content
    if not content:
        raise StructuredOutputError(
            "The AI model returned empty content."
        )

    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise StructuredOutputError(
            "The AI response was not valid JSON."
        ) from exc

    if not isinstance(result, dict):
        raise StructuredOutputError(
            "The AI response must be a JSON object."
        )
    return result
