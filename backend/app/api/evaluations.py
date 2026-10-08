"""Evaluations API endpoints."""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_role, AuthenticatedUser
from app.models.models import Evaluation, Candidate
from app.models.schemas import EvaluationCreate, EvaluationResponse, EvaluationListResponse, RuleEvaluationResult, LLMAdvisoryRequest, LLMAdvisoryResponse
from app.services.evaluation_service import EvaluationService
from app.services.llm_service import LLMService

router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])


def evaluation_to_response(e: Evaluation) -> EvaluationResponse:
    try: metrics = json.loads(e.metrics)
    except Exception: metrics = {}
    try: gate_results = [RuleEvaluationResult(**r) for r in json.loads(e.gate_results)]
    except Exception: gate_results = []
    return EvaluationResponse(
        id=e.id, candidate_id=e.candidate_id, policy_id=e.policy_id, benchmark_dataset=e.benchmark_dataset,
        dataset_hash=e.dataset_hash, metrics=metrics, gate_verdict=e.gate_verdict, gate_results=gate_results,
        readiness_score=e.readiness_score, summary=e.summary, executed_by=e.executed_by, executed_at=e.executed_at,
    )


@router.post("", response_model=EvaluationResponse, status_code=status.HTTP_201_CREATED)
def execute_evaluation(eval_in: EvaluationCreate, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_role("analyst"))):
    ev = EvaluationService.execute_evaluation(db, eval_in, user.username, user.role)
    return evaluation_to_response(ev)


@router.get("", response_model=EvaluationListResponse)
def list_evaluations(candidate_id: Optional[str] = None, verdict: Optional[str] = None, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_role("viewer"))):
    query = db.query(Evaluation)
    if candidate_id: query = query.filter(Evaluation.candidate_id == candidate_id)
    if verdict: query = query.filter(Evaluation.gate_verdict == verdict)
    items = query.order_by(Evaluation.executed_at.desc()).all()
    return EvaluationListResponse(items=[evaluation_to_response(e) for e in items], total=len(items))


@router.get("/{evaluation_id}", response_model=EvaluationResponse)
def get_evaluation(evaluation_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_role("viewer"))):
    ev = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
    if not ev: raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation_to_response(ev)


@router.post("/{evaluation_id}/advisory", response_model=LLMAdvisoryResponse)
async def get_llm_advisory(evaluation_id: str, req: Optional[LLMAdvisoryRequest] = None, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_role("viewer"))):
    ev = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
    if not ev: raise HTTPException(status_code=404, detail="Evaluation not found")
    cand = db.query(Candidate).filter(Candidate.id == ev.candidate_id).first()
    if not cand: raise HTTPException(status_code=404, detail="Candidate not found")

    res = await LLMService.generate_advisory(
        cand.name, cand.task_type, json.loads(ev.metrics), ev.gate_verdict,
        [r.get("message", "") for r in json.loads(ev.gate_results) if not r.get("passed", False)]
    )
    return LLMAdvisoryResponse(
        evaluation_id=ev.id, candidate_name=cand.name, advisory_summary=res["advisory_summary"],
        risk_level=res["risk_level"], recommendations=res["recommendations"], provider=res["provider"],
        model=res["model"], is_advisory_only=True
    )
