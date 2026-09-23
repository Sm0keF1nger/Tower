from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import KEYCLOAK_CLIENT_ID, KEYCLOAK_ISSUER, KEYCLOAK_JWKS_URL

bearer_scheme = HTTPBearer(auto_error=False, description="JWT-токен доступу від Keycloak")
_jwks_client = jwt.PyJWKClient(KEYCLOAK_JWKS_URL, cache_keys=True, lifespan=300)


@dataclass
class CurrentUser:
    sub: str
    username: str
    email: str | None
    display_name: str
    roles: list[str]

    @property
    def primary_role(self) -> str:
        return "admin" if "admin" in self.roles else "manager"


def _decode_token(token: str) -> dict:
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=KEYCLOAK_ISSUER,
            options={"verify_aud": False},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недійсний або прострочений токен авторизації.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    audience = payload.get("aud", [])
    if isinstance(audience, str):
        audience = [audience]
    authorized_party = payload.get("azp")
    if KEYCLOAK_CLIENT_ID not in audience and authorized_party != KEYCLOAK_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен видано для іншого клієнта.",
        )
    return payload


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Потрібна авторизація.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _decode_token(credentials.credentials)
    realm_roles = payload.get("realm_access", {}).get("roles", [])
    roles = [role for role in realm_roles if role in {"admin", "manager"}]
    if not roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Користувачу не призначено роль адміністратора або менеджера.",
        )

    return CurrentUser(
        sub=str(payload.get("sub", "")),
        username=str(payload.get("preferred_username") or payload.get("name") or "користувач"),
        email=payload.get("email"),
        display_name=str(payload.get("name") or payload.get("given_name") or payload.get("preferred_username") or "Користувач"),
        roles=roles,
    )


def require_roles(*allowed_roles: str) -> Callable:
    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not set(user.roles).intersection(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостатньо прав для виконання цієї дії.",
            )
        return user

    return dependency


require_manager_or_admin = require_roles("manager", "admin")
require_admin = require_roles("admin")
