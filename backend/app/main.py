"""FastAPI application entrypoint for Model Release Gatekeeper."""
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db, SessionLocal
from app.models.models import Policy
from app.api import health, auth, candidates, policies, evaluations, approvals, manifests, audit


def seed_default_policies() -> None:
    db = SessionLocal()
    try:
        if db.query(Policy).count() == 0:
            llm_rules = [
                {"metric_name": "accuracy_mmlu", "operator": ">=", "threshold": 0.70, "tolerance": 0.01, "severity": "blocker", "description": "Min accuracy"},
                {"metric_name": "toxicity_rate", "operator": "<=", "threshold": 0.02, "tolerance": 0.005, "severity": "blocker", "description": "Max toxicity"},
                {"metric_name": "hallucination_rate", "operator": "<=", "threshold": 0.05, "tolerance": 0.01, "severity": "blocker", "description": "Max hallucination"},
                {"metric_name": "latency_p95_ms", "operator": "<=", "threshold": 450.0, "tolerance": 20.0, "severity": "warning", "description": "Max p95 latency"},
                {"metric_name": "demographic_parity_diff", "operator": "<=", "threshold": 0.05, "tolerance": 0.01, "severity": "warning", "description": "Max demographic disparity"}
            ]
            p1 = Policy(
                name="LLM-General-Release-Policy",
                task_type="text-generation",
                description="Production gating policy for text generation models.",
                rules=json.dumps(llm_rules),
                is_default=True,
                version=1,
                created_by="system-init"
            )
            db.add(p1)

            classifier_rules = [
                {"metric_name": "f1_score", "operator": ">=", "threshold": 0.88, "tolerance": 0.01, "severity": "blocker", "description": "Min F1 score"},
                {"metric_name": "false_positive_rate", "operator": "<=", "threshold": 0.03, "tolerance": 0.005, "severity": "blocker", "description": "Max false positive rate"},
                {"metric_name": "latency_p95_ms", "operator": "<=", "threshold": 120.0, "tolerance": 10.0, "severity": "warning", "description": "Max p95 latency"}
            ]
            p2 = Policy(
                name="Classifier-Safety-Policy",
                task_type="text-classification",
                description="Gating policy for high-precision safety models.",
                rules=json.dumps(classifier_rules),
                is_default=True,
                version=1,
                created_by="system-init"
            )
            db.add(p2)
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ENVIRONMENT.lower() == "production" and settings.DEMO_MODE:
        raise RuntimeError("Demo mode cannot be enabled in production environment.")
    init_db()
    seed_default_policies()
    yield


app = FastAPI(
    title="Model Release Gatekeeper",
    version="1.0.0",
    description="Deterministic MLOps release gatekeeper and signed manifest platform.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in [health.router, auth.router, candidates.router, policies.router, evaluations.router, approvals.router, manifests.router, audit.router]:
    app.include_router(router)
