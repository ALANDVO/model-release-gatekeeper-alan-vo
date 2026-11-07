"""Policy configuration API endpoints."""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_role, AuthenticatedUser
from app.models.models import Policy, PolicyVersion
from app.models.schemas import PolicyCreate, PolicyUpdate, PolicyResponse, GateRule, PolicyVersionResponse, PolicyMigrationRequest, PolicyMigrationResponse
from app.services.audit_service import AuditService
from app.services.evaluation_service import EvaluationService
from app.models.schemas import EvaluationCreate

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


def version_to_response(v: PolicyVersion) -> PolicyVersionResponse:
    try:
        raw = json.loads(v.rules)
        rules = [GateRule(**r) for r in raw]
    except Exception:
        rules = []
    return PolicyVersionResponse(
        id=v.id, policy_id=v.policy_id, version_number=v.version_number,
        name=v.name, task_type=v.task_type, description=v.description,
        rules=rules, is_default=v.is_default, created_by=v.created_by,
        created_at=v.created_at, change_summary=v.change_summary,
    )


@router.get("/{policy_id}/versions", response_model=List[PolicyVersionResponse])
def list_policy_versions(policy_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_role("viewer"))):
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    versions = db.query(PolicyVersion).filter(PolicyVersion.policy_id == policy_id).order_by(PolicyVersion.version_number.desc()).all()
    return [version_to_response(v) for v in versions]


@router.get("/{policy_id}/versions/{version_number}", response_model=PolicyVersionResponse)
def get_policy_version(policy_id: str, version_number: int, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_role("viewer"))):
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    version = db.query(PolicyVersion).filter(PolicyVersion.policy_id == policy_id, PolicyVersion.version_number == version_number).first()
    if not version:
        raise HTTPException(status_code=404, detail="Policy version not found")
    return version_to_response(version)


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

    # Capture current state for version history before update
    old_rules = policy.rules
    old_description = policy.description
    old_is_default = policy.is_default
    version_number = policy.version

    changes = []
    if policy_update.description is not None:
        policy.description = policy_update.description
        changes.append("description")
    if policy_update.rules is not None:
        policy.rules = json.dumps([r.model_dump() for r in policy_update.rules])
        policy.version += 1
        changes.append("rules")
    if policy_update.is_default is not None:
        if policy_update.is_default:
            db.query(Policy).filter(Policy.task_type == policy.task_type, Policy.is_default == True).update({"is_default": False})
        policy.is_default = policy_update.is_default
        changes.append("is_default")

    # Create version history entry if there were actual changes
    if changes:
        version_entry = PolicyVersion(
            policy_id=policy.id,
            version_number=version_number,
            name=policy.name,
            task_type=policy.task_type,
            description=old_description,
            rules=old_rules,
            is_default=old_is_default,
            created_by=user.username,
            change_summary=f"Updated: {', '.join(changes)}",
        )
        db.add(version_entry)

    db.flush()
    AuditService.log(db, "POLICY_UPDATED", "policy", policy.id, user.username, user.role, {"version": policy.version, "changes": changes})
    return policy_to_response(policy)


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(policy_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_role("admin"))):
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    db.delete(policy)
    db.flush()


@router.post("/migrate-evaluation", response_model=PolicyMigrationResponse, status_code=status.HTTP_201_CREATED)
def migrate_evaluation(req: PolicyMigrationRequest, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_role("analyst"))):
    """Re-evaluate a candidate against a specific policy version."""
    # Verify candidate exists
    from app.models.models import Candidate, Evaluation
    candidate = db.query(Candidate).filter(Candidate.id == req.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Verify policy version exists
    policy_version = db.query(PolicyVersion).filter(PolicyVersion.id == req.target_policy_version_id).first()
    if not policy_version:
        raise HTTPException(status_code=404, detail="Policy version not found")

    # Get the previous evaluation for this candidate (if any)
    previous_evaluation = db.query(Evaluation).filter(Evaluation.candidate_id == req.candidate_id).order_by(Evaluation.executed_at.desc()).first()

    # Run new evaluation with the policy version's rules
    gate_rules = [GateRule(**r) for r in json.loads(policy_version.rules)]
    from app.services.gate_engine import GateEngine
    # We need metrics from the previous evaluation to re-evaluate
    if not previous_evaluation:
        raise HTTPException(status_code=400, detail="No previous evaluation found for candidate. Cannot migrate without metrics.")

    metrics = json.loads(previous_evaluation.metrics)
    verdict, rule_results, score, summary = GateEngine.evaluate_all(gate_rules, metrics)

    # Create new evaluation
    new_evaluation = Evaluation(
        candidate_id=candidate.id,
        policy_id=policy_version.policy_id,
        benchmark_dataset=previous_evaluation.benchmark_dataset,
        dataset_hash=previous_evaluation.dataset_hash,
        metrics=json.dumps(metrics),
        gate_verdict=verdict,
        gate_results=json.dumps([r.model_dump() for r in rule_results]),
        readiness_score=score,
        summary=f"[Migrated from policy version {policy_version.version_number}] {summary}",
        executed_by=user.username,
    )
    db.add(new_evaluation)
    candidate.status = "REJECTED" if verdict == "REJECTED" else "REVIEW_PENDING"
    db.flush()

    AuditService.log(db, "EVALUATION_MIGRATED", "evaluation", new_evaluation.id, user.username, user.role, {
        "candidate_id": req.candidate_id,
        "previous_evaluation_id": previous_evaluation.id if previous_evaluation else None,
        "policy_version_id": policy_version.id,
        "policy_version_number": policy_version.version_number,
    })

    return PolicyMigrationResponse(
        candidate_id=req.candidate_id,
        previous_evaluation_id=previous_evaluation.id if previous_evaluation else None,
        new_evaluation_id=new_evaluation.id,
        message=f"Candidate re-evaluated against policy version {policy_version.version_number}. Verdict: {verdict}",
    )
