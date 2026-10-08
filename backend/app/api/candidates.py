"""Candidates API endpoints."""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.core.security import require_role, AuthenticatedUser
from app.models.models import Candidate
from app.models.schemas import CandidateCreate, CandidateUpdate, CandidateResponse, CandidateListResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


def candidate_to_response(c: Candidate) -> CandidateResponse:
    try:
        tags = json.loads(c.tags)
    except Exception:
        tags = []
    return CandidateResponse(
        id=c.id, name=c.name, version=c.version, task_type=c.task_type,
        base_model=c.base_model, artifact_uri=c.artifact_uri, artifact_hash=c.artifact_hash,
        description=c.description, tags=tags, status=c.status, created_by=c.created_by,
        created_at=c.created_at, updated_at=c.updated_at,
    )


@router.get("", response_model=CandidateListResponse)
def list_candidates(
    task_type: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role("viewer")),
):
    query = db.query(Candidate)
    if task_type:
        query = query.filter(Candidate.task_type == task_type)
    if status_filter:
        query = query.filter(Candidate.status == status_filter)
    if search:
        s = f"%{search}%"
        query = query.filter(or_(Candidate.name.ilike(s), Candidate.base_model.ilike(s)))
    total = query.count()
    items = query.order_by(Candidate.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return CandidateListResponse(items=[candidate_to_response(c) for c in items], total=total, page=page, page_size=page_size)


@router.post("", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
def create_candidate(
    candidate_in: CandidateCreate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role("analyst")),
):
    existing = db.query(Candidate).filter(Candidate.name == candidate_in.name, Candidate.version == candidate_in.version).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Candidate '{candidate_in.name}' v{candidate_in.version} already exists.")
    candidate = Candidate(
        name=candidate_in.name, version=candidate_in.version, task_type=candidate_in.task_type,
        base_model=candidate_in.base_model, artifact_uri=candidate_in.artifact_uri, artifact_hash=candidate_in.artifact_hash,
        description=candidate_in.description, tags=json.dumps(candidate_in.tags), status="DRAFT", created_by=user.username,
    )
    db.add(candidate)
    db.flush()
    AuditService.log(db, "CANDIDATE_CREATED", "candidate", candidate.id, user.username, user.role, {"name": candidate.name})
    return candidate_to_response(candidate)


@router.get("/{candidate_id}", response_model=CandidateResponse)
def get_candidate(candidate_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_role("viewer"))):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate_to_response(candidate)


@router.patch("/{candidate_id}", response_model=CandidateResponse)
def update_candidate(
    candidate_id: str, candidate_update: CandidateUpdate, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_role("analyst")),
):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if candidate_update.description is not None:
        candidate.description = candidate_update.description
    if candidate_update.tags is not None:
        candidate.tags = json.dumps(candidate_update.tags)
    if candidate_update.status is not None:
        candidate.status = candidate_update.status
    db.flush()
    return candidate_to_response(candidate)


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(candidate_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_role("admin"))):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    db.delete(candidate)
    db.flush()
    AuditService.log(db, "CANDIDATE_DELETED", "candidate", candidate_id, user.username, user.role)
