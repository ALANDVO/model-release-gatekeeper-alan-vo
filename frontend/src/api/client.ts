import {
  AuthConfig, TokenResponse, UserInfo, Candidate, CandidateCreate, CandidateUpdate,
  CandidateListResponse, Policy, PolicyCreate, Evaluation, EvaluationCreate,
  EvaluationListResponse, Approval, ApprovalCreate, ReleaseManifest,
  ManifestVerifyRequest, ManifestVerifyResponse, AuditLogListResponse, LLMAdvisoryResponse,
} from './types';

let inMemoryToken: string | null = null;
export const setAuthToken = (token: string | null) => { inMemoryToken = token; };
export const getAuthToken = (): string | null => inMemoryToken;

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', 'application/json');
  if (inMemoryToken) headers.set('Authorization', `Bearer ${inMemoryToken}`);

  const resp = await fetch(path, { ...options, headers });
  if (!resp.ok) {
    let err = resp.statusText;
    try { const j = await resp.json(); err = j.detail || JSON.stringify(j); } catch {}
    throw new Error(`API Error (${resp.status}): ${err}`);
  }
  if (resp.status === 204) return {} as T;
  return resp.json();
}

export const api = {
  getAuthConfig: () => request<AuthConfig>('/api/auth/config'),
  demoLogin: (username: string, email: string, role: string) =>
    request<TokenResponse>('/api/auth/demo-login', { method: 'POST', body: JSON.stringify({ username, email, role }) }),
  exchangeToken: (code: string, code_verifier: string, redirect_uri: string) =>
    request<TokenResponse>('/api/auth/token', { method: 'POST', body: JSON.stringify({ code, code_verifier, redirect_uri }) }),
  getUserInfo: () => request<UserInfo>('/api/auth/userinfo'),

  listCandidates: (p: { task_type?: string; status?: string; search?: string } = {}) => {
    const q = new URLSearchParams();
    if (p.task_type) q.set('task_type', p.task_type);
    if (p.status) q.set('status', p.status);
    if (p.search) q.set('search', p.search);
    return request<CandidateListResponse>(`/api/candidates?${q.toString()}`);
  },
  getCandidate: (id: string) => request<Candidate>(`/api/candidates/${id}`),
  createCandidate: (data: CandidateCreate) => request<Candidate>('/api/candidates', { method: 'POST', body: JSON.stringify(data) }),
  updateCandidate: (id: string, data: CandidateUpdate) => request<Candidate>(`/api/candidates/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteCandidate: (id: string) => request<void>(`/api/candidates/${id}`, { method: 'DELETE' }),

  listPolicies: (task_type?: string) => request<Policy[]>(`/api/policies${task_type ? `?task_type=${encodeURIComponent(task_type)}` : ''}`),
  getPolicy: (id: string) => request<Policy>(`/api/policies/${id}`),
  createPolicy: (data: PolicyCreate) => request<Policy>('/api/policies', { method: 'POST', body: JSON.stringify(data) }),
  deletePolicy: (id: string) => request<void>(`/api/policies/${id}`, { method: 'DELETE' }),

  executeEvaluation: (data: EvaluationCreate) => request<Evaluation>('/api/evaluations', { method: 'POST', body: JSON.stringify(data) }),
  listEvaluations: (candidate_id?: string) => request<EvaluationListResponse>(`/api/evaluations${candidate_id ? `?candidate_id=${encodeURIComponent(candidate_id)}` : ''}`),
  getEvaluation: (id: string) => request<Evaluation>(`/api/evaluations/${id}`),
  getLLMAdvisory: (evaluationId: string) => request<LLMAdvisoryResponse>(`/api/evaluations/${evaluationId}/advisory`, { method: 'POST', body: JSON.stringify({ evaluation_id: evaluationId }) }),

  recordApproval: (data: ApprovalCreate) => request<Approval>('/api/approvals', { method: 'POST', body: JSON.stringify(data) }),
  listApprovals: (candidateId?: string) => request<Approval[]>(`/api/approvals${candidateId ? `?candidate_id=${encodeURIComponent(candidateId)}` : ''}`),

  exportManifest: (candidate_id: string, evaluation_id: string) => request<ReleaseManifest>('/api/manifests/export', { method: 'POST', body: JSON.stringify({ candidate_id, evaluation_id }) }),
  getManifest: (id: string) => request<ReleaseManifest>(`/api/manifests/${id}`),
  verifyManifest: (data: ManifestVerifyRequest) => request<ManifestVerifyResponse>('/api/manifests/verify', { method: 'POST', body: JSON.stringify(data) }),
  getManifestDownloadUrl: (id: string, format: 'json' | 'yaml') => `/api/manifests/${id}/download?format=${format}`,

  listAuditLogs: (entity_type?: string) => request<AuditLogListResponse>(`/api/audit${entity_type ? `?entity_type=${encodeURIComponent(entity_type)}` : ''}`),
};
