from fastapi import APIRouter

from app.api.routes.analysis import router as analysis_router
from app.api.routes.capa import router as capa_router
from app.api.routes.copilot import router as copilot_router
from app.api.routes.documents import router as documents_router
from app.api.routes.evidence import router as evidence_router
from app.api.routes.ingestion import router as ingestion_router
from app.api.routes.investigations import (
    router as investigations_router,
)
from app.api.routes.rca import router as rca_router
from app.api.routes.review import router as review_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(investigations_router)
api_router.include_router(documents_router)
api_router.include_router(evidence_router)
api_router.include_router(analysis_router)
api_router.include_router(rca_router)
api_router.include_router(review_router)
api_router.include_router(capa_router)
api_router.include_router(ingestion_router)
api_router.include_router(copilot_router)
