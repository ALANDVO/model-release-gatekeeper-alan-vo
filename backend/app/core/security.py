"""Security, role-based authorization, and token verification utilities."""
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)

ROLE_HIERARCHY: Dict[str, int] = {"viewer": 1, "analyst": 2, "admin": 3}


class AuthenticatedUser:
    def __init__(self, user_id: str, username: str, email: str, role: str, is_demo: bool = False):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.role = role.lower()
        self.is_demo = is_demo

    def has_role(self, required_role: str) -> bool:
        return ROLE_HIERARCHY.get(self.role, 0) >= ROLE_HIERARCHY.get(required_role.lower(), 999)

    def to_dict(self) -> Dict[str, Any]:
        return {"user_id": self.user_id, "username": self.username, "email": self.email, "role": self.role, "is_demo": self.is_demo}


def create_demo_token(username: str, email: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    if not settings.DEMO_MODE:
        raise RuntimeError("Demo token creation is prohibited when DEMO_MODE is disabled.")
    expires = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=8))
    claims = {
        "sub": username, "preferred_username": username, "email": email,
        "realm_access": {"roles": [role]}, "roles": [role],
        "iss": "gatekeeper-demo-issuer", "aud": settings.OIDC_AUDIENCE,
        "exp": expires, "iat": datetime.now(timezone.utc), "demo": True,
    }
    return jwt.encode(claims, settings.DEMO_JWT_SECRET, algorithm="HS256")


def compute_hmac_signature(payload_str: str) -> str:
    return hmac.new(settings.SIGNING_KEY.encode(), payload_str.encode(), hashlib.sha256).hexdigest()


def verify_hmac_signature(payload_str: str, expected_signature: str) -> bool:
    return hmac.compare_digest(compute_hmac_signature(payload_str), expected_signature)


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> AuthenticatedUser:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Missing Bearer authentication token", headers={"WWW-Authenticate": "Bearer"})

    raw_token = credentials.credentials
    if settings.DEMO_MODE:
        try:
            payload = jwt.decode(raw_token, settings.DEMO_JWT_SECRET, algorithms=["HS256"], audience=settings.OIDC_AUDIENCE, options={"verify_aud": False})
            if payload.get("demo") is True:
                roles = payload.get("roles") or payload.get("realm_access", {}).get("roles", ["viewer"])
                role = "admin" if "admin" in roles else ("analyst" if "analyst" in roles else "viewer")
                return AuthenticatedUser(
                    user_id=payload.get("sub", "demo-user"),
                    username=payload.get("preferred_username", payload.get("sub", "demo-user")),
                    email=payload.get("email", "demo@example.com"),
                    role=role, is_demo=True
                )
        except JWTError:
            pass

    from app.core.oidc import verify_oidc_token
    try:
        payload = await verify_oidc_token(raw_token)
        roles = []
        if "realm_access" in payload and "roles" in payload["realm_access"]:
            roles.extend(payload["realm_access"]["roles"])
        if "roles" in payload:
            roles.extend(payload["roles"])
        role = "admin" if "admin" in roles else ("analyst" if "analyst" in roles else "viewer")
        return AuthenticatedUser(
            user_id=payload.get("sub", "unknown"),
            username=payload.get("preferred_username", payload.get("sub", "unknown")),
            email=payload.get("email", ""),
            role=role, is_demo=False
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {str(exc)}", headers={"WWW-Authenticate": "Bearer"})


def require_role(min_role: str):
    def role_dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not user.has_role(min_role):
            raise HTTPException(status_code=403, detail=f"Access denied: '{min_role}' role required.")
        return user
    return role_dependency
