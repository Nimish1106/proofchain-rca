from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """
    Central application configuration.

    Priority:
    1. Environment variables
    2. Project-root .env
    3. Defined defaults
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "ProofChain RCA"
    app_env: Literal[
        "development",
        "test",
        "production",
    ] = "development"

    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # CORS
    cors_origins: str = "http://localhost:5173"

    # Database
    database_url: str | None = None

    # Groq
    groq_api_key: SecretStr | None = None
    groq_model: str | None = None
    groq_timeout_seconds: float = 60.0
    groq_max_retries: int = 2
    groq_extraction_chunk_chars: int = 12000
    groq_extraction_overlap_chars: int = 500

    # RCA context configuration
    rca_max_context_chars: int = 60000
    rca_max_evidence_items: int = 200

    # Document storage
    storage_dir: Path = Path("var/uploads")

    # Upload limits
    max_upload_size_mb: int = 15
    max_pdf_pages: int = 500
    max_extracted_text_chars: int = 5_000_000

    @field_validator(
        "database_url",
        "groq_model",
        mode="before",
    )
    @classmethod
    def normalize_optional_strings(cls, value):
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("groq_api_key", mode="before")
    @classmethod
    def normalize_api_key(cls, value):
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("max_upload_size_mb")
    @classmethod
    def validate_upload_size(cls, value: int) -> int:
        if not 1 <= value <= 100:
            raise ValueError(
                "Upload size must be between 1 and 100 MB."
            )
        return value

    @field_validator("max_pdf_pages")
    @classmethod
    def validate_pdf_pages(cls, value: int) -> int:
        if not 1 <= value <= 5000:
            raise ValueError(
                "Maximum PDF pages must be between 1 and 5000."
            )
        return value

    @field_validator("max_extracted_text_chars")
    @classmethod
    def validate_text_limit(cls, value: int) -> int:
        if value < 1000:
            raise ValueError(
                "Extracted text limit must be at least 1000."
            )
        return value

    @field_validator("groq_timeout_seconds")
    @classmethod
    def validate_groq_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError(
                "Groq timeout must be positive."
            )
        return value

    @field_validator("groq_max_retries")
    @classmethod
    def validate_groq_retries(cls, value: int) -> int:
        if not 0 <= value <= 5:
            raise ValueError(
                "Groq retries must be between 0 and 5."
            )
        return value

    @field_validator("groq_extraction_chunk_chars")
    @classmethod
    def validate_extraction_chunk_size(cls, value: int) -> int:
        if not 1000 <= value <= 50000:
            raise ValueError(
                "Extraction chunk size must be between 1000 and 50000."
            )
        return value

    @field_validator("groq_extraction_overlap_chars")
    @classmethod
    def validate_extraction_overlap(cls, value: int) -> int:
        if value < 0:
            raise ValueError(
                "Extraction overlap cannot be negative."
            )
        return value

    @model_validator(mode="after")
    def validate_chunk_configuration(self):
        if (
            self.groq_extraction_overlap_chars
            >= self.groq_extraction_chunk_chars
        ):
            raise ValueError(
                "Extraction overlap must be smaller than chunk size."
            )
        return self

    @field_validator("rca_max_context_chars")
    @classmethod
    def validate_rca_context_size(cls, value: int) -> int:
        if not 5000 <= value <= 200000:
            raise ValueError(
                "RCA context size must be between 5000 and 200000 characters."
            )
        return value

    @field_validator("rca_max_evidence_items")
    @classmethod
    def validate_rca_evidence_count(cls, value: int) -> int:
        if not 1 <= value <= 1000:
            raise ValueError(
                "RCA evidence count must be between 1 and 1000."
            )
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def resolved_storage_dir(self) -> Path:
        if self.storage_dir.is_absolute():
            return self.storage_dir
        return PROJECT_ROOT / self.storage_dir

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
