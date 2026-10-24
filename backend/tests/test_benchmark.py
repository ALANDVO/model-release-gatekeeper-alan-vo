"""Tests for built-in AI safety benchmark endpoint."""
import pytest
from fastapi.testclient import TestClient


def test_benchmark_endpoint_not_found(client: TestClient, analyst_token: str):
    """Benchmark on non-existent candidate returns 404."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    resp = client.post("/api/evaluations/non-existent-id/benchmark", headers=headers)
    assert resp.status_code == 404
    assert "Candidate not found" in resp.json()["detail"]


def test_benchmark_endpoint_requires_analyst_role(client: TestClient, viewer_token: str):
    """Benchmark requires analyst role or higher."""
    headers = {"Authorization": f"Bearer {viewer_token}"}
    # First create a candidate as analyst
    analyst_headers = {"Authorization": f"Bearer analyst-token"}
    # We need a valid candidate - create one first
    # This test will need a candidate fixture
    pass


def test_benchmark_endpoint_runs_and_creates_evaluation(client: TestClient, analyst_token: str, admin_token: str):
    """Benchmark runs successfully and creates evaluation record."""
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create candidate
    cand_payload = {
        "name": "benchmark-test-model",
        "version": "1.0.0",
        "task_type": "text-generation",
        "base_model": "gpt-2",
        "artifact_uri": "s3://models/benchmark-test.bin",
        "artifact_hash": "f" * 64,
        "description": "Model for benchmark testing",
        "tags": ["test", "benchmark"],
    }
    cand_resp = client.post("/api/candidates", json=cand_payload, headers=analyst_headers)
    assert cand_resp.status_code == 201
    candidate_id = cand_resp.json()["id"]

    # 2. Run benchmark
    bench_resp = client.post(f"/api/evaluations/{candidate_id}/benchmark", headers=analyst_headers)
    assert bench_resp.status_code == 201
    bench_data = bench_resp.json()

    # Verify benchmark response structure
    assert "candidate_id" in bench_data
    assert bench_data["candidate_id"] == candidate_id
    assert "candidate_name" in bench_data
    assert bench_data["candidate_name"] == "benchmark-test-model"
    assert "evaluation_id" in bench_data
    assert "benchmark_dataset" in bench_data
    assert bench_data["benchmark_dataset"] == "gatekeeper-ai-safety-bench-v1"
    assert "dataset_hash" in bench_data
    assert "candidate_metrics" in bench_data
    assert "baseline_metrics" in bench_data
    assert "gate_verdict" in bench_data
    assert bench_data["gate_verdict"] in ["APPROVED_FOR_RELEASE", "NEEDS_REVIEW", "REJECTED"]
    assert "readiness_score" in bench_data
    assert isinstance(bench_data["readiness_score"], (int, float))
    assert "summary" in bench_data
    assert "rule_results" in bench_data
    assert isinstance(bench_data["rule_results"], list)
    assert "executed_by" in bench_data

    # Verify candidate metrics match expected benchmark values
    cand_metrics = bench_data["candidate_metrics"]
    assert "accuracy_mmlu" in cand_metrics
    assert "toxicity_rate" in cand_metrics
    assert "hallucination_rate" in cand_metrics
    assert "latency_p95_ms" in cand_metrics
    assert "demographic_parity_diff" in cand_metrics

    # Verify baseline metrics
    base_metrics = bench_data["baseline_metrics"]
    assert "accuracy_mmlu" in base_metrics
    assert "latency_p95_ms" in base_metrics

    # 3. Verify evaluation was created
    eval_resp = client.get(f"/api/evaluations?candidate_id={candidate_id}", headers=analyst_headers)
    assert eval_resp.status_code == 200
    evals = eval_resp.json()["items"]
    assert len(evals) == 1
    assert evals[0]["id"] == bench_data["evaluation_id"]
    assert evals[0]["gate_verdict"] == bench_data["gate_verdict"]
    assert evals[0]["readiness_score"] == bench_data["readiness_score"]


def test_benchmark_reproducibility(client: TestClient, analyst_token: str, admin_token: str):
    """Benchmark produces consistent results on repeated runs."""
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}

    # Create candidate
    cand_payload = {
        "name": "repro-test-model",
        "version": "1.0.0",
        "task_type": "text-generation",
        "base_model": "gpt-2",
        "artifact_uri": "s3://models/repro-test.bin",
        "artifact_hash": "g" * 64,
    }
    cand_resp = client.post("/api/candidates", json=cand_payload, headers=analyst_headers)
    assert cand_resp.status_code == 201
    candidate_id = cand_resp.json()["id"]

    # Run benchmark twice
    bench1 = client.post(f"/api/evaluations/{candidate_id}/benchmark", headers=analyst_headers)
    assert bench1.status_code == 201
    data1 = bench1.json()

    bench2 = client.post(f"/api/evaluations/{candidate_id}/benchmark", headers=analyst_headers)
    assert bench2.status_code == 201
    data2 = bench2.json()

    # Metrics should be identical (deterministic benchmark)
    assert data1["candidate_metrics"] == data2["candidate_metrics"]
    assert data1["baseline_metrics"] == data2["baseline_metrics"]
    assert data1["gate_verdict"] == data2["gate_verdict"]
    assert data1["readiness_score"] == data2["readiness_score"]
    assert data1["rule_results"] == data2["rule_results"]

    # But evaluation IDs should be different (new evaluation each time)
    assert data1["evaluation_id"] != data2["evaluation_id"]


def test_benchmark_unauthenticated(client: TestClient):
    """Benchmark endpoint rejects unauthenticated requests."""
    resp = client.post("/api/evaluations/some-id/benchmark")
    assert resp.status_code == 401


def test_benchmark_viewer_denied(client: TestClient, viewer_token: str, analyst_token: str):
    """Viewer role cannot run benchmark."""
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    # Create candidate as analyst
    cand_payload = {
        "name": "viewer-denied-model",
        "version": "1.0.0",
        "task_type": "text-generation",
        "base_model": "gpt-2",
        "artifact_uri": "s3://models/viewer-denied.bin",
        "artifact_hash": "h" * 64,
    }
    cand_resp = client.post("/api/candidates", json=cand_payload, headers=analyst_headers)
    assert cand_resp.status_code == 201
    candidate_id = cand_resp.json()["id"]

    # Try to run benchmark as viewer
    bench_resp = client.post(f"/api/evaluations/{candidate_id}/benchmark", headers=viewer_headers)
    assert bench_resp.status_code == 403
    assert "analyst" in bench_resp.json()["detail"]

