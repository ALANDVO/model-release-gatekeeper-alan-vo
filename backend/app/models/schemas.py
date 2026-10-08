"""Pydantic schemas for request validation and response serialization."""
from datetime import datetime
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class AuthConfigResponse(BaseModel):
    issuer_url: str
    client_id: str
    audience: str
    demo_mode: bool
    environment: str


class DemoLoginRequest(BaseModel):
    username: str
    email: str
    role: Literal["viewer", "analyst", "admin"] = "analyst"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    role: str
    username: str


class UserInfoResponse(BaseModel):
    user_id: str
    username: str
    email: str
    role: str
    is_demo: bool


class GateRule(BaseModel):
    metric_name: str
    operator: Literal[">=", "<=", "==", "!=", ">", "<", "in_range"] = ">="
    threshold: float
    tolerance: float = 0.0
    severity: Literal["blocker", "warning", "info"] = "blocker"
    description: str = ""


class RuleEvaluationResult(BaseModel):
    metric_name: str
    operator: str
    threshold: float
    actual_value: Optional[float] = None
    passed: bool
    severity: str
    message: str


class CandidateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    version: str = Field(min_length=1, max_length=50)
    task_type: str = Field(min_length=2, max_length=50)
    base_model: str = Field(min_length=1, max_length=120)
    artifact_uri: str = Field(min_length=1, max_length=255)
    artifact_hash: str = Field(min_length=8, max_length=64)
    description: str = ""
    tags: List[str] = Field(default_factory=list)


class CandidateUpdate(BaseModel):
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None


class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    version: str
    task_type: str
    base_model: str
    artifact_uri: str
    artifact_hash: str
    description: str
    tags: List[str]
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class CandidateListResponse(BaseModel):
    items: List[CandidateResponse]
    total: int
    page: int
    page_size: int


class PolicyCreate(BaseModel):
    name: str
    task_type: str
    description: str = ""
    rules: List[GateRule]
    is_default: bool = False


class PolicyUpdate(BaseModel):
    description: Optional[str] = None
    rules: Optional[List[GateRule]] = None
    is_default: Optional[bool] = None


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    task_type: str
    description: str
    rules: List[GateRule]
    is_default: bool
    version: int
    created_by: str
    created_at: datetime
    updated_at: datetime


class EvaluationCreate(BaseModel):
    candidate_id: str
    policy_id: Optional[str] = None
    benchmark_dataset: str
    dataset_hash: str
    metrics: Dict[str, float]


class EvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    candidate_id: str
    policy_id: str
    benchmark_dataset: str
    dataset_hash: str
    metrics: Dict[str, float]
    gate_verdict: str
    gate_results: List[RuleEvaluationResult]
    readiness_score: float
    summary: str
    executed_by: str
    executed_at: datetime


class EvaluationListResponse(BaseModel):
    items: List[EvaluationResponse]
    total: int


class ApprovalCreate(BaseModel):
    evaluation_id: str
    reviewer_role: Literal["ml_engineer", "safety_lead", "release_manager"]
    decision: Literal["APPROVED", "REJECTED", "CHANGES_REQUESTED"]
    comments: str = ""


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    candidate_id: str
    evaluation_id: str
    reviewer_id: str
    reviewer_role: str
    decision: str
    comments: str
    signature: str
    signed_at: datetime


class ManifestExportRequest(BaseModel):
    candidate_id: str
    evaluation_id: str


class ManifestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    candidate_id: str
    evaluation_id: str
    manifest_json: Dict[str, Any]
    manifest_hash: str
    signature: str
    status: str
    exported_by: str
    exported_at: datetime


class ManifestVerifyRequest(BaseModel):
    manifest_json: Dict[str, Any]
    expected_hash: Optional[str] = None
    signature: Optional[str] = None


class ManifestVerifyResponse(BaseModel):
    valid: bool
    computed_hash: str
    hash_match: bool
    signature_valid: bool
    verdict: str
    details: Dict[str, Any]


class LLMAdvisoryRequest(BaseModel):
    evaluation_id: str
    focus_area: Optional[str] = "general-release-risk"


class LLMAdvisoryResponse(BaseModel):
    evaluation_id: str
    candidate_name: str
    advisory_summary: str
    risk_level: str
    recommendations: List[str]
    provider: str
    model: str
    is_advisory_only: bool = True


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    action: str
    entity_type: str
    entity_id: str
    actor_id: str
    actor_role: str
    details: Dict[str, Any]
    timestamp: datetime


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
