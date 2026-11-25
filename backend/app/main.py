from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.app_env)

app = FastAPI(
    title=settings.app_name,
    description=(
        "AI-powered Root Cause Analysis "
        "for pharmaceutical API manufacturing."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=[
        "GET",
        "POST",
        "PATCH",
        "DELETE",
    ],
    allow_headers=[
        "Content-Type",
        "Authorization",
    ],
)

app.include_router(api_router)


@app.get("/api/v1/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Application liveness check."""
    return {
        "status": "ok",
        "service": "proofchain-rca-api",
    }
