# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

policy-versioning

## Roadmap

### continue-implementation — Continue implementation and resolve known failures

Status: done

Acceptance:
- Run checks, fix failures, and implement the next planned feature

Implementation: `backend/app/api/evaluations.py`, `backend/tests/conftest.py`, `frontend/src/api/client.ts`, `frontend/src/components/CandidateDetail.tsx`

Tests: `backend/tests/test_benchmark.py`, `backend/tests/test_api_workflows.py`, `backend/tests/test_auth_and_oidc.py`, `backend/tests/test_gate_engine.py`, `backend/tests/test_llm_adapters.py`, `backend/tests/test_manifest_service.py`, `frontend/src/test/AuthPKCE.test.tsx`, `frontend/src/test/CandidateList.test.tsx`, `frontend/src/test/ManifestVerification.test.tsx`

### policy-versioning — Policy version management and migration

Status: done

Acceptance:
- CRUD API for policy versions with proper versioning
- Policy migration endpoint for candidate re-evaluation
- Audit trail for policy changes

Implementation: `backend/app/models/models.py`, `backend/app/models/schemas.py`, `backend/app/api/policies.py`, `backend/tests/conftest.py`

Tests: `backend/tests/test_api_workflows.py::test_policy_versioning_and_migration`

