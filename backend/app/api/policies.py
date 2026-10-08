"""Policy configuration API endpoints."""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_role, AuthenticatedUser
from app.models.models import Policy
from app.models.schemas import PolicyCreate, PolicyUpdate, PolicyResponse, GateRule
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/policies", tags=["policies"])


def policy_to_response(p: Policy) -> PolicyResponse:
    try:
        raw = json.loads(p.rules)
        rules = [GateRule(**r) for r in raw]
    except Exception:
        rules = []
    return PolicyResponse(
        id=p.id, name=p.name, task_type=p.task_type, description=p.description,
        rules=rules, is_default=p.is_default, version=p.version, created_by=p.created_by,
        created_at=p.created_at, updated_at=p.updated_at,
    )


@router.get("", response_model=List[PolicyResponse])
def list_policies(task_type: Optional[str] = None, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_role("viewer"))):
    query = db.query(Policy)
    if task_type:
        query = query.filter(Policy.task_type == task_type)
    return [policy_to_response(p) for p in query.order_by(Policy.created_at.desc()).all()]


@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(policy_in: PolicyCreate, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_role("admin"))):
    if db.query(Policy).filter(Policy.name == policy_in.name).first():
        raise HTTPException(status_code=409, detail=f"Policy '{policy_in.name}' already exists.")
    if policy_in.is_default:
        db.query(Policy).filter(Policy.task_type == policy_in.task_type, Policy.is_default == True).update({"is_default": False})

    rules_json = json.dumps([r.model_dump() for r in policy_in.rules])
    policy = Policy(
        name=policy_in.name, task_type=policy_in.task_type, description=policy_in.description,
        rules=rules_json, is_default=policy_in.is_default, version=1, created_by=user.username,
    )
    db.add(policy)
    db.flush()
    AuditService.log(db, "POLICY_CREATED", "policy", policy.id, user.username, user.role, {"name": policy.name})
    return policy_to_response(policy)


@router.get("/{policy_id}", response_model=PolicyResponse)
def get_policy(policy_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_role("viewer"))):
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy_to_response(policy)


@router.put("/{policy_id}", response_model=PolicyResponse)
def update_policy(policy_id: str, policy_update: PolicyUpdate, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_role("admin"))):
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    if policy_update.description is not None:
        policy.description = policy_update.description
    if policy_update.rules is not None:
        policy.rules = json.dumps([r.model_dump() for r in policy_update.rules])
        policy.version += 1
    if policy_update.is_default is not None:
        if policy_update.is_default:
            db.query(Policy).filter(Policy.task_type == policy.task_type, Policy.is_default == True).update({"is_default": False})
        policy.is_default = policy_update.is_default
    db.flush()
    AuditService.log(db, "POLICY_UPDATED", "policy", policy.id, user.username, user.role, {"version": policy.version})
    return policy_to_response(policy)


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(policy_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_role("admin"))):
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    db.delete(policy)
    db.flush()
