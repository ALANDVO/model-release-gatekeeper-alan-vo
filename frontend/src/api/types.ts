export type Role = 'viewer' | 'analyst' | 'admin';
export type CandidateStatus = 'DRAFT' | 'EVALUATED' | 'REVIEW_PENDING' | 'APPROVED' | 'REJECTED';
export type GateVerdict = 'APPROVED_FOR_RELEASE' | 'NEEDS_REVIEW' | 'REJECTED';
export type Severity = 'blocker' | 'warning' | 'info';
export type Operator = '>=' | '<=' | '==' | '!=' | '>' | '<' | 'in_range';

export interface UserInfo {
  user_id: string; username: string; email: string; role: Role; is_demo: boolean;
}

export interface AuthConfig {
  issuer_url: string; client_id: string; audience: string; demo_mode: boolean; environment: string;
}

export interface TokenResponse {
  access_token: string; token_type: string; expires_in: number; role: Role; username: string;
}

export interface Candidate {
  id: string; name: string; version: string; task_type: string; base_model: string;
  artifact_uri: string; artifact_hash: string; description: string; tags: string[];
  status: CandidateStatus; created_by: string; created_at: string; updated_at: string;
}

export interface CandidateCreate {
  name: string; version: string; task_type: string; base_model: string;
  artifact_uri: string; artifact_hash: string; description?: string; tags?: string[];
}

export interface CandidateUpdate {
  description?: string; tags?: string[]; status?: CandidateStatus;
}

export interface CandidateListResponse {
  items: Candidate[]; total: number; page: number; page_size: number;
}

export interface GateRule {
  metric_name: string; operator: Operator; threshold: number; tolerance: number; severity: Severity; description?: string;
}

export interface Policy {
  id: string; name: string; task_type: string; description: string; rules: GateRule[];
  is_default: boolean; version: number; created_by: string; created_at: string; updated_at: string;
}

export interface PolicyCreate {
  name: string; task_type: string; description?: string; rules: GateRule[]; is_default?: boolean;
}

export interface RuleEvaluationResult {
  metric_name: string; operator: string; threshold: number; actual_value?: number | null;
  passed: boolean; severity: Severity; message: string;
}

export interface Evaluation {
  id: string; candidate_id: string; policy_id: string; benchmark_dataset: string;
  dataset_hash: string; metrics: Record<string, number>; gate_verdict: GateVerdict;
  gate_results: RuleEvaluationResult[]; readiness_score: number; summary: string;
  executed_by: string; executed_at: string;
}

export interface EvaluationCreate {
  candidate_id: string; policy_id?: string; benchmark_dataset: string; dataset_hash: string; metrics: Record<string, number>;
}

export interface EvaluationListResponse {
  items: Evaluation[]; total: number;
}

export interface Approval {
  id: string; candidate_id: string; evaluation_id: string; reviewer_id: string;
  reviewer_role: string; decision: 'APPROVED' | 'REJECTED' | 'CHANGES_REQUESTED';
  comments: string; signature: string; signed_at: string;
}

export interface ApprovalCreate {
  evaluation_id: string; reviewer_role: 'ml_engineer' | 'safety_lead' | 'release_manager';
  decision: 'APPROVED' | 'REJECTED' | 'CHANGES_REQUESTED'; comments?: string;
}

export interface ReleaseManifest {
  id: string; candidate_id: string; evaluation_id: string; manifest_json: Record<string, unknown>;
  manifest_hash: string; signature: string; status: string; exported_by: string; exported_at: string;
}

export interface ManifestVerifyRequest {
  manifest_json: Record<string, unknown>; expected_hash?: string; signature?: string;
}

export interface ManifestVerifyResponse {
  valid: boolean; computed_hash: string; hash_match: boolean; signature_valid: boolean;
  verdict: string; details: Record<string, unknown>;
}

export interface AuditLog {
  id: string; action: string; entity_type: string; entity_id: string;
  actor_id: string; actor_role: string; details: Record<string, unknown>; timestamp: string;
}

export interface AuditLogListResponse {
  items: AuditLog[]; total: number;
}

export interface LLMAdvisoryResponse {
  evaluation_id: string; candidate_name: string; advisory_summary: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH'; recommendations: string[]; provider: string; model: string; is_advisory_only: boolean;
}
