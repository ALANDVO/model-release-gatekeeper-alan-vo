"""Evaluation execution service."""
import json
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.models import Candidate, Policy, Evaluation
from app.models.schemas import EvaluationCreate, GateRule
from app.services.gate_engine import GateEngine
from app.services.audit_service import AuditService


class EvaluationService:
    @staticmethod
    def execute_evaluation(db: Session, eval_in: EvaluationCreate, actor_id: str, actor_role: str) -> Evaluation:
        candidate = db.query(Candidate).filter(Candidate.id == eval_in.candidate_id).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found.")

        policy = None
        if eval_in.policy_id:
            policy = db.query(Policy).filter(Policy.id == eval_in.policy_id).first()
        else:
            policy = db.query(Policy).filter(Policy.task_type == candidate.task_type, Policy.is_default == True).first()
            if not policy:
                policy = db.query(Policy).filter(Policy.is_default == True).first()

        if not policy:
            raise HTTPException(status_code=400, detail="No policy found for evaluation.")

        gate_rules = [GateRule(**r) for r in json.loads(policy.rules)]
        verdict, rule_results, score, summary = GateEngine.evaluate_all(gate_rules, eval_in.metrics)

        evaluation = Evaluation(
            candidate_id=candidate.id, policy_id=policy.id, benchmark_dataset=eval_in.benchmark_dataset,
            dataset_hash=eval_in.dataset_hash, metrics=json.dumps(eval_in.metrics), gate_verdict=verdict,
            gate_results=json.dumps([r.model_dump() for r in rule_results]), readiness_score=score,
            summary=summary, executed_by=actor_id,
        )
        db.add(evaluation)
        candidate.status = "REJECTED" if verdict == "REJECTED" else "REVIEW_PENDING"
        db.flush()

        AuditService.log(db, "EVALUATION_EXECUTED", "evaluation", evaluation.id, actor_id, actor_role, {"verdict": verdict})
        return evaluation
