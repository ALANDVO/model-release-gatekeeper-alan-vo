"""Release manifests API endpoints."""
import json
import yaml
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_role, AuthenticatedUser
from app.models.models import ReleaseManifest
from app.models.schemas import (
    ManifestExportRequest, ManifestResponse, ManifestVerifyRequest, ManifestVerifyResponse
)
from app.services.manifest_service import ManifestService

router = APIRouter(prefix="/api/manifests", tags=["manifests"])


def manifest_to_response(m: ReleaseManifest) -> ManifestResponse:
    """Format ORM model into schema response."""
    payload = {}
    try:
        payload = json.loads(m.manifest_json)
    except Exception:
        payload = {}

    return ManifestResponse(
        id=m.id,
        candidate_id=m.candidate_id,
        evaluation_id=m.evaluation_id,
        manifest_json=payload,
        manifest_hash=m.manifest_hash,
        signature=m.signature,
        status=m.status,
        exported_by=m.exported_by,
        exported_at=m.exported_at,
    )


@router.post("/export", response_model=ManifestResponse, status_code=status.HTTP_201_CREATED)
def export_manifest(
    req: ManifestExportRequest,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role("admin")),
):
    """Compile and cryptographically sign a release manifest (admin role required)."""
    manifest = ManifestService.generate_manifest(
        db=db,
        candidate_id=req.candidate_id,
        evaluation_id=req.evaluation_id,
        actor_id=user.username,
        actor_role=user.role,
    )
    return manifest_to_response(manifest)


@router.get("/{manifest_id}", response_model=ManifestResponse)
def get_manifest(
    manifest_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role("viewer")),
):
    """Get manifest details by ID."""
    manifest = db.query(ReleaseManifest).filter(ReleaseManifest.id == manifest_id).first()
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found")
    return manifest_to_response(manifest)


@router.get("/{manifest_id}/download")
def download_manifest(
    manifest_id: str,
    format: str = Query("json", pattern="^(json|yaml)$"),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role("viewer")),
):
    """Download manifest file formatted as JSON or YAML."""
    manifest = db.query(ReleaseManifest).filter(ReleaseManifest.id == manifest_id).first()
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found")

    payload = json.loads(manifest.manifest_json)
    # Include metadata envelope
    export_doc = {
        "manifest": payload,
        "digest": {
            "algorithm": "sha256",
            "hash": manifest.manifest_hash,
            "signature": manifest.signature,
            "status": manifest.status,
            "exported_at": manifest.exported_at.isoformat(),
        }
    }

    if format == "yaml":
        content = yaml.dump(export_doc, sort_keys=False)
        media_type = "application/x-yaml"
        filename = f"release-manifest-{manifest.id[:8]}.yaml"
    else:
        content = json.dumps(export_doc, indent=2)
        media_type = "application/json"
        filename = f"release-manifest-{manifest.id[:8]}.json"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/verify", response_model=ManifestVerifyResponse)
def verify_manifest(
    req: ManifestVerifyRequest,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role("viewer")),
):
    """Verify an external release manifest for tamper-evidence and valid digest."""
    result = ManifestService.verify_manifest(
        db=db,
        manifest_data=req.manifest_json,
        expected_hash=req.expected_hash,
        signature=req.signature,
    )
    return ManifestVerifyResponse(**result)
