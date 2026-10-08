"""Audit trail API endpoints."""
import json
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_role, AuthenticatedUser
from app.models.models import AuditLog
from app.models.schemas import AuditLogResponse, AuditLogListResponse

router = APIRouter(prefix="/api/audit", tags=["audit"])


def audit_to_response(a: AuditLog) -> AuditLogResponse:
    """Format ORM model into schema response."""
    details = {}
    try:
        details = json.loads(a.details)
    except Exception:
        details = {}

    return AuditLogResponse(
        id=a.id,
        action=a.action,
        entity_type=a.entity_type,
        entity_id=a.entity_id,
        actor_id=a.actor_id,
        actor_role=a.actor_role,
        details=details,
        timestamp=a.timestamp,
    )


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role("viewer")),
):
    """Retrieve immutable audit log history."""
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if action:
        query = query.filter(AuditLog.action == action)

    total = query.count()
    items = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

    return AuditLogListResponse(
        items=[audit_to_response(a) for a in items],
        total=total
    )
