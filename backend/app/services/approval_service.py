"""Approval workflow service with cryptographic HMAC signing."""
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.models import Candidate, Evaluation, Approval
from app.models.schemas import ApprovalCreate
from app.core.security import compute_hmac_signature
from app.services.audit_service import AuditService


class ApprovalService:
    @staticmethod
    def record_approval(db: Session, approval_in: ApprovalCreate, reviewer_id: str, actor_role: str) -> Approval:
        evaluation = db.query(Evaluation).filter(Evaluation.id == approval_in.evaluation_id).first()
        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found.")
        candidate = db.query(Candidate).filter(Candidate.id == evaluation.candidate_id).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found.")

        existing = db.query(Approval).filter(
            Approval.evaluation_id == evaluation.id,
            Approval.reviewer_id == reviewer_id,
            Approval.reviewer_role == approval_in.reviewer_role
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Duplicate sign-off for role '{approval_in.reviewer_role}'.")

        now = datetime.now(timezone.utc)
        sig_str = f"cand={candidate.id};eval={evaluation.id};rev={reviewer_id};role={approval_in.reviewer_role};dec={approval_in.decision};time={now.isoformat()}"
        sig = compute_hmac_signature(sig_str)

        approval = Approval(
            candidate_id=candidate.id, evaluation_id=evaluation.id, reviewer_id=reviewer_id,
            reviewer_role=approval_in.reviewer_role, decision=approval_in.decision, comments=approval_in.comments,
            signature=sig, signed_at=now,
        )
        db.add(approval)
        db.flush()

        if approval_in.decision == "REJECTED":
            candidate.status = "REJECTED"
        elif approval_in.decision == "APPROVED":
            approvals = db.query(Approval).filter(Approval.evaluation_id == evaluation.id, Approval.decision == "APPROVED").all()
            roles = {a.reviewer_role for a in approvals}
            if "release_manager" in roles or len(roles) >= 2:
                candidate.status = "APPROVED"

        db.flush()
        AuditService.log(db, "APPROVAL_RECORDED", "approval", approval.id, reviewer_id, actor_role, {"decision": approval.decision})
        return approval
