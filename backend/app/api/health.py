"""Health and diagnostic endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint verifying database connectivity."""
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "demo_mode": settings.DEMO_MODE,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_configured": bool(settings.LLM_API_KEY),
    }
