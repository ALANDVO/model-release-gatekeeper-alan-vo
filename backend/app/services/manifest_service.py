"""Release manifest export and verification service."""
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.models import Candidate, Evaluation, Approval, ReleaseManifest
from app.core.security import compute_hmac_signature, verify_hmac_signature
from app.services.audit_service import AuditService


class ManifestService:
    @staticmethod
    def canonical_json_bytes(data: Dict[str, Any]) -> bytes:
        return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")

    @classmethod
    def compute_hash(cls, data: Dict[str, Any]) -> str:
        return hashlib.sha256(cls.canonical_json_bytes(data)).hexdigest()

    @classmethod
    def generate_manifest(cls, db: Session, candidate_id: str, evaluation_id: str, actor_id: str, actor_role: str) -> ReleaseManifest:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        evaluation = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found")

        approvals = db.query(Approval).filter(Approval.evaluation_id == evaluation.id).all()
        issued_at = datetime.now(timezone.utc).isoformat()
        manifest_payload: Dict[str, Any] = {
            "schema_version": "1.0.0",
            "generator": "Model Release Gatekeeper",
            "author": "Alan Vo <alanvo@gmail.com>",
            "issued_at": issued_at,
            "candidate": {
                "id": candidate.id,
                "name": candidate.name,
                "version": candidate.version,
                "task_type": candidate.task_type,
                "base_model": candidate.base_model,
                "artifact_uri": candidate.artifact_uri,
                "artifact_hash": candidate.artifact_hash,
                "status": candidate.status,
            },
            "evaluation": {
                "id": evaluation.id,
                "policy_id": evaluation.policy_id,
                "benchmark_dataset": evaluation.benchmark_dataset,
                "dataset_hash": evaluation.dataset_hash,
                "metrics": json.loads(evaluation.metrics),
                "gate_verdict": evaluation.gate_verdict,
                "readiness_score": evaluation.readiness_score,
                "executed_at": evaluation.executed_at.isoformat(),
                "executed_by": evaluation.executed_by,
            },
            "approvals": [
                {
                    "reviewer_id": a.reviewer_id,
                    "reviewer_role": a.reviewer_role,
                    "decision": a.decision,
                    "signature": a.signature,
                    "signed_at": a.signed_at.isoformat(),
                }
                for a in approvals
            ],
            "release_verdict": "APPROVED" if candidate.status == "APPROVED" else evaluation.gate_verdict,
        }

        m_hash = cls.compute_hash(manifest_payload)
        sig = compute_hmac_signature(m_hash)
        manifest = ReleaseManifest(
            candidate_id=candidate.id,
            evaluation_id=evaluation.id,
            manifest_json=json.dumps(manifest_payload),
            manifest_hash=m_hash,
            signature=sig,
            status="SIGNED",
            exported_by=actor_id,
        )
        db.add(manifest)
        db.flush()

        AuditService.log(
            db=db,
            action="MANIFEST_EXPORTED",
            entity_type="manifest",
            entity_id=manifest.id,
            actor_id=actor_id,
            actor_role=actor_role,
            details={"candidate_id": candidate.id, "manifest_hash": m_hash}
        )
        return manifest

    @classmethod
    def verify_manifest(cls, db: Session, manifest_data: Dict[str, Any], expected_hash: Optional[str] = None, signature: Optional[str] = None) -> Dict[str, Any]:
        c_hash = cls.compute_hash(manifest_data)
        hash_match = (c_hash == expected_hash) if expected_hash else True
        sig_valid = False
        if signature:
            sig_valid = verify_hmac_signature(c_hash, signature)
        else:
            rec = db.query(ReleaseManifest).filter(ReleaseManifest.manifest_hash == c_hash).first()
            if rec:
                sig_valid = verify_hmac_signature(c_hash, rec.signature)

        valid = hash_match and (sig_valid if signature else True)
        return {
            "valid": valid,
            "computed_hash": c_hash,
            "hash_match": hash_match,
            "signature_valid": sig_valid,
            "verdict": "VERIFIED_VALID" if valid else "TAMPER_DETECTED",
            "details": {"release_verdict": manifest_data.get("release_verdict")}
        }
