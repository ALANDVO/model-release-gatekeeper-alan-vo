"""OpenID Connect (OIDC) client and token verification utilities."""
import time
from typing import Dict, Any, Optional
import httpx
from jose import jwt, jwk
from app.core.config import settings

_oidc_cache: Optional[Dict[str, Any]] = None
_oidc_expiry: float = 0.0
_jwks_cache: Optional[Dict[str, Any]] = None
_jwks_expiry: float = 0.0


async def get_oidc_configuration() -> Dict[str, Any]:
    global _oidc_cache, _oidc_expiry
    now = time.time()
    if _oidc_cache and now < _oidc_expiry:
        return _oidc_cache
    url = f"{settings.OIDC_ISSUER_URL.rstrip('/')}/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        _oidc_cache = resp.json()
        _oidc_expiry = now + 300
        return _oidc_cache


async def get_jwks() -> Dict[str, Any]:
    global _jwks_cache, _jwks_expiry
    now = time.time()
    if _jwks_cache and now < _jwks_expiry:
        return _jwks_cache
    cfg = await get_oidc_configuration()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(cfg["jwks_uri"])
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_expiry = now + 300
        return _jwks_cache


async def verify_oidc_token(token: str) -> Dict[str, Any]:
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    if not kid: raise ValueError("Token header missing kid")
    jwks = await get_jwks()
    k_dict = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if not k_dict: raise ValueError(f"No key for kid {kid}")
    pk = jwk.construct(k_dict)
    return jwt.decode(
        token, pk.to_pem().decode(), algorithms=[header.get("alg", "RS256")],
        issuer=settings.OIDC_ISSUER_URL, audience=settings.OIDC_AUDIENCE, options={"verify_exp": True}
    )


async def exchange_authorization_code(code: str, code_verifier: str, redirect_uri: str) -> Dict[str, Any]:
    cfg = await get_oidc_configuration()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            cfg["token_endpoint"],
            data={"grant_type": "authorization_code", "client_id": settings.OIDC_CLIENT_ID, "code": code, "code_verifier": code_verifier, "redirect_uri": redirect_uri},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if resp.status_code != 200: raise ValueError(f"Exchange failed: {resp.text}")
        return resp.json()
