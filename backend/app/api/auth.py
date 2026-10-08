"""Authentication endpoints supporting OIDC PKCE exchange and local demo mode."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.core.config import settings
from app.core.security import create_demo_token, get_current_user, AuthenticatedUser
from app.core.oidc import exchange_authorization_code
from app.models.schemas import (
    AuthConfigResponse, DemoLoginRequest, TokenResponse, UserInfoResponse
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class TokenExchangeRequest(BaseModel):
    code: str
    code_verifier: str
    redirect_uri: str


@router.get("/config", response_model=AuthConfigResponse)
def get_auth_config():
    """Return public OIDC client configuration and demo mode status."""
    return AuthConfigResponse(
        issuer_url=settings.OIDC_ISSUER_URL,
        client_id=settings.OIDC_CLIENT_ID,
        audience=settings.OIDC_AUDIENCE,
        demo_mode=settings.DEMO_MODE,
        environment=settings.ENVIRONMENT,
    )


@router.post("/demo-login", response_model=TokenResponse)
def demo_login(req: DemoLoginRequest):
    """Local demo login endpoint. Refused if DEMO_MODE is false or in production."""
    if not settings.DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo login is disabled in this environment."
        )

    token = create_demo_token(
        username=req.username,
        email=req.email,
        role=req.role
    )

    return TokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in=28800,  # 8 hours
        role=req.role,
        username=req.username,
    )


@router.post("/token")
async def exchange_token(req: TokenExchangeRequest):
    """Exchange OIDC authorization code and PKCE verifier for bearer tokens."""
    try:
        tokens = await exchange_authorization_code(
            code=req.code,
            code_verifier=req.code_verifier,
            redirect_uri=req.redirect_uri
        )
        return tokens
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token exchange failed: {str(exc)}"
        )


@router.get("/userinfo", response_model=UserInfoResponse)
def get_user_info(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Return identity and assigned role for the authenticated user."""
    return UserInfoResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        is_demo=current_user.is_demo,
    )
