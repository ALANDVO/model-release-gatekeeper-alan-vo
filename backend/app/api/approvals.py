"""Approvals API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_role, AuthenticatedUser
from app.models.models import Approval
from app.models.schemas import ApprovalCreate, ApprovalResponse
from app.services.approval_service import ApprovalService

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


def approval_to_response(a: Approval) -> ApprovalResponse:
    """Format ORM model into schema response."""
    return ApprovalResponse(
        id=a.id,
        candidate_id=a.candidate_id,
        evaluation_id=a.evaluation_id,
        reviewer_id=a.reviewer_id,
        reviewer_role=a.reviewer_role,
        decision=a.decision,
        comments=a.comments,
        signature=a.signature,
        signed_at=a.signed_at,
    )


@router.post("", response_model=ApprovalResponse, status_code=status.HTTP_201_CREATED)
def record_approval(
    approval_in: ApprovalCreate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role("analyst")),
):
    """Submit a stakeholder sign-off with HMAC digital signature."""
    # Release manager approvals require admin role
    if approval_in.reviewer_role == "release_manager" and not user.has_role("admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Release manager approvals require 'admin' role privileges."
        )

    approval = ApprovalService.record_approval(
        db=db,
        approval_in=approval_in,
        reviewer_id=user.username,
        actor_role=user.role,
    )
    return approval_to_response(approval)


@router.get("", response_model=List[ApprovalResponse])
def list_approvals(
    evaluation_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role("viewer")),
):
    """List approval sign-offs."""
    query = db.query(Approval)
    if evaluation_id:
        query = query.filter(Approval.evaluation_id == evaluation_id)
    if candidate_id:
        query = query.filter(Approval.candidate_id == candidate_id)

    items = query.order_by(Approval.signed_at.desc()).all()
    return [approval_to_response(a) for a in items]
