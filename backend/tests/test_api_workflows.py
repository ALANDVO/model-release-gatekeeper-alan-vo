"""End-to-end API workflows and boundary input testing across real HTTP boundaries."""
from fastapi.testclient import TestClient


def test_full_release_gating_lifecycle(
    client: TestClient,
    analyst_token: str,
    admin_token: str,
    viewer_token: str
):
    """Test full create -> evaluate -> approve -> export -> verify workflow."""
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    # 1. Register candidate
    cand_payload = {
        "name": "roberta-sentiment-production",
        "version": "1.2.0",
        "task_type": "text-classification",
        "base_model": "roberta-base",
        "artifact_uri": "s3://models/roberta-sentiment-v1.2.0.pt",
        "artifact_hash": "b" * 64,
        "description": "Fine-tuned sentiment model with low latency",
        "tags": ["nlp", "sentiment", "prod"]
    }
    cand_resp = client.post("/api/candidates", json=cand_payload, headers=analyst_headers)
    assert cand_resp.status_code == 201
    cand_data = cand_resp.json()
    candidate_id = cand_data["id"]
    assert cand_data["status"] == "DRAFT"

    # 2. Admin creates a targeted policy
    policy_payload = {
        "name": "Strict-Classification-Policy-v1",
        "task_type": "text-classification",
        "description": "High accuracy and latency gate",
        "rules": [
            {
                "metric_name": "f1_score",
                "operator": ">=",
                "threshold": 0.90,
                "tolerance": 0.01,
                "severity": "blocker",
                "description": "Macro F1 must exceed 90%"
            },
            {
                "metric_name": "latency_p95_ms",
                "operator": "<=",
                "threshold": 100.0,
                "tolerance": 5.0,
                "severity": "warning",
                "description": "p95 latency limit"
            }
        ],
        "is_default": False
    }
    pol_resp = client.post("/api/policies", json=policy_payload, headers=admin_headers)
    assert pol_resp.status_code == 201
    policy_id = pol_resp.json()["id"]

    # 3. Analyst runs evaluation
    eval_payload = {
        "candidate_id": candidate_id,
        "policy_id": policy_id,
        "benchmark_dataset": "sst2-validation",
        "dataset_hash": "c" * 64,
        "metrics": {
            "f1_score": 0.925,
            "latency_p95_ms": 85.0
        }
    }
    eval_resp = client.post("/api/evaluations", json=eval_payload, headers=analyst_headers)
    assert eval_resp.status_code == 201
    eval_data = eval_resp.json()
    evaluation_id = eval_data["id"]
    assert eval_data["gate_verdict"] == "APPROVED_FOR_RELEASE"
    assert eval_data["readiness_score"] == 100.0

    # 4. Stakeholder sign-offs
    # ML Engineer approval
    app1_resp = client.post("/api/approvals", json={
        "evaluation_id": evaluation_id,
        "reviewer_role": "ml_engineer",
        "decision": "APPROVED",
        "comments": "Model meets all benchmark standards."
    }, headers=analyst_headers)
    assert app1_resp.status_code == 201
    assert app1_resp.json()["signature"] != ""

    # Release manager approval (admin role)
    app2_resp = client.post("/api/approvals", json={
        "evaluation_id": evaluation_id,
        "reviewer_role": "release_manager",
        "decision": "APPROVED",
        "comments": "Final sign-off granted for deployment."
    }, headers=admin_headers)
    assert app2_resp.status_code == 201

    # Check candidate is now APPROVED
    cand_updated = client.get(f"/api/candidates/{candidate_id}", headers=viewer_headers)
    assert cand_updated.status_code == 200
    assert cand_updated.json()["status"] == "APPROVED"

    # 5. Export signed release manifest
    manifest_resp = client.post("/api/manifests/export", json={
        "candidate_id": candidate_id,
        "evaluation_id": evaluation_id,
    }, headers=admin_headers)
    assert manifest_resp.status_code == 201
    manifest_data = manifest_resp.json()
    manifest_id = manifest_data["id"]
    manifest_hash = manifest_data["manifest_hash"]
    manifest_sig = manifest_data["signature"]
    assert len(manifest_hash) == 64

    # 6. Verify manifest
    verify_resp = client.post("/api/manifests/verify", json={
        "manifest_json": manifest_data["manifest_json"],
        "expected_hash": manifest_hash,
        "signature": manifest_sig
    }, headers=viewer_headers)
    assert verify_resp.status_code == 200
    assert verify_resp.json()["valid"] is True
    assert verify_resp.json()["verdict"] == "VERIFIED_VALID"

    # 7. Check audit log records
    audit_resp = client.get("/api/audit", headers=viewer_headers)
    assert audit_resp.status_code == 200
    logs = audit_resp.json()["items"]
    actions = [l["action"] for l in logs]
    assert "CANDIDATE_CREATED" in actions
    assert "EVALUATION_EXECUTED" in actions
    assert "APPROVAL_RECORDED" in actions
    assert "MANIFEST_EXPORTED" in actions


def test_boundary_duplicate_candidate_rejection(client: TestClient, analyst_token: str):
    headers = {"Authorization": f"Bearer {analyst_token}"}
    payload = {
        "name": "duplicate-model",
        "version": "1.0.0",
        "task_type": "text-generation",
        "base_model": "gpt-2",
        "artifact_uri": "s3://models/gpt2.bin",
        "artifact_hash": "d" * 64,
    }
    resp1 = client.post("/api/candidates", json=payload, headers=headers)
    assert resp1.status_code == 201

    # Duplicate submission
    resp2 = client.post("/api/candidates", json=payload, headers=headers)
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"]


def test_boundary_missing_candidate_evaluation(client: TestClient, analyst_token: str):
    headers = {"Authorization": f"Bearer {analyst_token}"}
    payload = {
        "candidate_id": "non-existent-id-0000",
        "benchmark_dataset": "test-set",
        "dataset_hash": "e" * 64,
        "metrics": {"acc": 0.9}
    }
    resp = client.post("/api/evaluations", json=payload, headers=headers)
    assert resp.status_code == 404
