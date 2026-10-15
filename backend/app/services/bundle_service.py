"""Candidate bundle export/import service for portability across environments."""
import json
from datetime import datetime, timezone
from typing import Dict
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.models import Candidate, Evaluation, Approval, ReleaseManifest
from app.models.schemas import (
    CandidateBundleExport, CandidateBundleImport, CandidateBundleImportResponse,
    CandidateResponse, EvaluationResponse, ApprovalResponse, ManifestResponse,
)
from app.services.audit_service import AuditService


class BundleService:
    @classmethod
    def export_bundle(cls, db: Session, candidate_id: str, actor_id: str, actor_role: str) -> CandidateBundleExport:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate: raise HTTPException(status_code=404, detail="Candidate not found")
        evaluations = db.query(Evaluation).filter(Evaluation.candidate_id == candidate_id).all()
        approvals = db.query(Approval).filter(Approval.candidate_id == candidate_id).all()
        manifests = db.query(ReleaseManifest).filter(ReleaseManifest.candidate_id == candidate_id).all()

        def eval_to_response(e: Evaluation) -> EvaluationResponse:
            try: metrics = json.loads(e.metrics)
            except Exception: metrics = {}
            try: gate_results = [r for r in json.loads(e.gate_results)]
            except Exception: gate_results = []
            return EvaluationResponse(id=e.id, candidate_id=e.candidate_id, policy_id=e.policy_id,
                benchmark_dataset=e.benchmark_dataset, dataset_hash=e.dataset_hash, metrics=metrics,
                gate_verdict=e.gate_verdict, gate_results=gate_results, readiness_score=e.readiness_score,
                summary=e.summary, executed_by=e.executed_by, executed_at=e.executed_at)

        def approval_to_response(a: Approval) -> ApprovalResponse:
            return ApprovalResponse(id=a.id, candidate_id=a.candidate_id, evaluation_id=a.evaluation_id,
                reviewer_id=a.reviewer_id, reviewer_role=a.reviewer_role, decision=a.decision,
                comments=a.comments, signature=a.signature, signed_at=a.signed_at)

        def manifest_to_response(m: ReleaseManifest) -> ManifestResponse:
            try: payload = json.loads(m.manifest_json)
            except Exception: payload = {}
            return ManifestResponse(id=m.id, candidate_id=m.candidate_id, evaluation_id=m.evaluation_id,
                manifest_json=payload, manifest_hash=m.manifest_hash, signature=m.signature,
                status=m.status, exported_by=m.exported_by, exported_at=m.exported_at)

        bundle = CandidateBundleExport(
            exported_at=datetime.now(timezone.utc), exported_by=actor_id,
            candidate=CandidateResponse(id=candidate.id, name=candidate.name, version=candidate.version,
                task_type=candidate.task_type, base_model=candidate.base_model,
                artifact_uri=candidate.artifact_uri, artifact_hash=candidate.artifact_hash,
                description=candidate.description, tags=json.loads(candidate.tags) if candidate.tags else [],
                status=candidate.status, created_by=candidate.created_by,
                created_at=candidate.created_at, updated_at=candidate.updated_at),
            evaluations=[eval_to_response(e) for e in evaluations],
            approvals=[approval_to_response(a) for a in approvals],
            manifests=[manifest_to_response(m) for m in manifests],
        )

        AuditService.log(db, "BUNDLE_EXPORTED", "candidate", candidate_id, actor_id, actor_role,
            {"evaluation_count": len(evaluations), "approval_count": len(approvals), "manifest_count": len(manifests)})
        return bundle

    @classmethod
    def import_bundle(cls, db: Session, import_req: CandidateBundleImport, actor_id: str, actor_role: str) -> CandidateBundleImportResponse:
        bundle = import_req.bundle
        existing = db.query(Candidate).filter(Candidate.name == bundle.candidate.name, Candidate.version == bundle.candidate.version).first()

        if existing and not import_req.import_as_new:
            candidate = existing
            candidate.description = bundle.candidate.description
            candidate.tags = json.dumps(bundle.candidate.tags)
            candidate.status = bundle.candidate.status
            candidate.updated_at = datetime.now(timezone.utc)
        else:
            import_version = bundle.candidate.version
            if existing and import_req.import_as_new:
                import_version = f"{bundle.candidate.version}-import-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            candidate = Candidate(name=bundle.candidate.name, version=import_version,
                task_type=bundle.candidate.task_type, base_model=bundle.candidate.base_model,
                artifact_uri=bundle.candidate.artifact_uri, artifact_hash=bundle.candidate.artifact_hash,
                description=bundle.candidate.description, tags=json.dumps(bundle.candidate.tags),
                status=bundle.candidate.status, created_by=actor_id)
            db.add(candidate)
            db.flush()

        imported_evals = imported_approvals = imported_manifests = 0
        eval_id_map: Dict[str, str] = {}

        for eval_resp in bundle.evaluations:
            eval_new = Evaluation(candidate_id=candidate.id, policy_id=eval_resp.policy_id,
                benchmark_dataset=eval_resp.benchmark_dataset, dataset_hash=eval_resp.dataset_hash,
                metrics=json.dumps(eval_resp.metrics), gate_verdict=eval_resp.gate_verdict,
                gate_results=json.dumps([r.model_dump() for r in eval_resp.gate_results]),
                readiness_score=eval_resp.readiness_score, summary=eval_resp.summary,
                executed_by=eval_resp.executed_by)
            db.add(eval_new)
            db.flush()
            eval_id_map[eval_resp.id] = eval_new.id
            imported_evals += 1

        for approval_resp in bundle.approvals:
            new_eval_id = eval_id_map.get(approval_resp.evaluation_id)
            if new_eval_id:
                db.add(Approval(candidate_id=candidate.id, evaluation_id=new_eval_id,
                    reviewer_id=approval_resp.reviewer_id, reviewer_role=approval_resp.reviewer_role,
                    decision=approval_resp.decision, comments=approval_resp.comments,
                    signature=approval_resp.signature))
                imported_approvals += 1

        for manifest_resp in bundle.manifests:
            new_eval_id = eval_id_map.get(manifest_resp.evaluation_id)
            if new_eval_id:
                db.add(ReleaseManifest(candidate_id=candidate.id, evaluation_id=new_eval_id,
                    manifest_json=json.dumps(manifest_resp.manifest_json),
                    manifest_hash=manifest_resp.manifest_hash, signature=manifest_resp.signature,
                    exported_by=actor_id))
                imported_manifests += 1

        db.flush()
        AuditService.log(db, "BUNDLE_IMPORTED", "candidate", candidate.id, actor_id, actor_role,
            {"source_candidate_id": bundle.candidate.id, "imported_evaluations": imported_evals,
             "imported_approvals": imported_approvals, "imported_manifests": imported_manifests,
             "import_as_new": import_req.import_as_new})

        return CandidateBundleImportResponse(candidate_id=candidate.id, imported_evaluations=imported_evals,
            imported_approvals=imported_approvals, imported_manifests=imported_manifests,
            message=f"Bundle imported successfully as candidate {candidate.name} v{candidate.version}")