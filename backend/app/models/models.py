"""SQLAlchemy database models for Model Release Gatekeeper."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Candidate(Base):
    __tablename__ = "candidates"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(120), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    task_type = Column(String(50), nullable=False, index=True)
    base_model = Column(String(120), nullable=False)
    artifact_uri = Column(String(255), nullable=False)
    artifact_hash = Column(String(64), nullable=False)
    description = Column(Text, nullable=False, default="")
    tags = Column(Text, nullable=False, default="[]")
    status = Column(String(30), nullable=False, default="DRAFT", index=True)
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    evaluations = relationship("Evaluation", back_populates="candidate", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="candidate", cascade="all, delete-orphan")
    manifests = relationship("ReleaseManifest", back_populates="candidate", cascade="all, delete-orphan")


class Policy(Base):
    __tablename__ = "policies"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(120), nullable=False, unique=True, index=True)
    task_type = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=False, default="")
    rules = Column(Text, nullable=False, default="[]")
    is_default = Column(Boolean, nullable=False, default=False)
    version = Column(Integer, nullable=False, default=1)
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    evaluations = relationship("Evaluation", back_populates="policy")


class Evaluation(Base):
    __tablename__ = "evaluations"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id = Column(String(36), ForeignKey("candidates.id"), nullable=False, index=True)
    policy_id = Column(String(36), ForeignKey("policies.id"), nullable=False, index=True)
    benchmark_dataset = Column(String(120), nullable=False)
    dataset_hash = Column(String(64), nullable=False)
    metrics = Column(Text, nullable=False, default="{}")
    gate_verdict = Column(String(30), nullable=False, index=True)
    gate_results = Column(Text, nullable=False, default="[]")
    readiness_score = Column(Float, nullable=False, default=0.0)
    summary = Column(Text, nullable=False, default="")
    executed_by = Column(String(100), nullable=False)
    executed_at = Column(DateTime, nullable=False, default=utc_now)

    candidate = relationship("Candidate", back_populates="evaluations")
    policy = relationship("Policy", back_populates="evaluations")
    approvals = relationship("Approval", back_populates="evaluation")
    manifests = relationship("ReleaseManifest", back_populates="evaluation")


class Approval(Base):
    __tablename__ = "approvals"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id = Column(String(36), ForeignKey("candidates.id"), nullable=False, index=True)
    evaluation_id = Column(String(36), ForeignKey("evaluations.id"), nullable=False, index=True)
    reviewer_id = Column(String(100), nullable=False)
    reviewer_role = Column(String(50), nullable=False)
    decision = Column(String(30), nullable=False)
    comments = Column(Text, nullable=False, default="")
    signature = Column(String(64), nullable=False)
    signed_at = Column(DateTime, nullable=False, default=utc_now)

    candidate = relationship("Candidate", back_populates="approvals")
    evaluation = relationship("Evaluation", back_populates="approvals")


class ReleaseManifest(Base):
    __tablename__ = "release_manifests"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id = Column(String(36), ForeignKey("candidates.id"), nullable=False, index=True)
    evaluation_id = Column(String(36), ForeignKey("evaluations.id"), nullable=False, index=True)
    manifest_json = Column(Text, nullable=False)
    manifest_hash = Column(String(64), nullable=False, index=True)
    signature = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, default="SIGNED")
    exported_by = Column(String(100), nullable=False)
    exported_at = Column(DateTime, nullable=False, default=utc_now)

    candidate = relationship("Candidate", back_populates="manifests")
    evaluation = relationship("Evaluation", back_populates="manifests")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    action = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(String(36), nullable=False, index=True)
    actor_id = Column(String(100), nullable=False)
    actor_role = Column(String(50), nullable=False)
    details = Column(Text, nullable=False, default="{}")
    timestamp = Column(DateTime, nullable=False, default=utc_now, index=True)


Index("idx_candidate_name_version", Candidate.name, Candidate.version, unique=True)
