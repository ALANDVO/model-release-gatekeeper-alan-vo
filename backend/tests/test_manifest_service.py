"""Unit tests for release manifest compilation, canonical hashing, and verification."""
import copy
from app.services.manifest_service import ManifestService
from app.core.security import compute_hmac_signature, verify_hmac_signature


def test_canonical_json_determinism():
    dict1 = {"b": 2, "a": 1, "nested": {"z": 26, "y": 25}}
    dict2 = {"nested": {"y": 25, "z": 26}, "a": 1, "b": 2}

    bytes1 = ManifestService.canonical_json_bytes(dict1)
    bytes2 = ManifestService.canonical_json_bytes(dict2)

    assert bytes1 == bytes2
    assert ManifestService.compute_hash(dict1) == ManifestService.compute_hash(dict2)


def test_manifest_tamper_detection(db_session):
    manifest_payload = {
        "schema_version": "1.0.0",
        "candidate": {"id": "c1", "name": "safety-model", "version": "1.0.0"},
        "evaluation": {"gate_verdict": "APPROVED_FOR_RELEASE", "readiness_score": 98.5},
        "release_verdict": "APPROVED"
    }

    original_hash = ManifestService.compute_hash(manifest_payload)
    sig = compute_hmac_signature(original_hash)

    # Valid check
    verify_res = ManifestService.verify_manifest(
        db=db_session,
        manifest_data=manifest_payload,
        expected_hash=original_hash,
        signature=sig,
    )
    assert verify_res["valid"] is True
    assert verify_res["verdict"] == "VERIFIED_VALID"

    # Tampered payload
    tampered_payload = copy.deepcopy(manifest_payload)
    tampered_payload["candidate"]["name"] = "unauthorized-replacement-model"

    tampered_res = ManifestService.verify_manifest(
        db=db_session,
        manifest_data=tampered_payload,
        expected_hash=original_hash,
        signature=sig,
    )
    assert tampered_res["valid"] is False
    assert tampered_res["verdict"] == "TAMPER_DETECTED"
    assert tampered_res["hash_match"] is False
