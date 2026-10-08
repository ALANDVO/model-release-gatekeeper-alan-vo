"""Audit logging service."""
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import AuditLog


class AuditService:
    """Records immutable audit trail entries."""

    @staticmethod
    def log(
        db: Session,
        action: str,
        entity_type: str,
        entity_id: str,
        actor_id: str,
        actor_role: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Create and persist an audit log entry."""
        entry = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            actor_role=actor_role,
            details=json.dumps(details or {}),
            timestamp=datetime.now(timezone.utc),
        )
        db.add(entry)
        db.flush()
        return entry
