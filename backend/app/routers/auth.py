from __future__ import annotations

from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.auth.security import CurrentUser, get_current_user
from app.config import (
    COOKIE_SECURE,
    KEYCLOAK_AUTHORIZE_URL,
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_LOGOUT_URL,
    KEYCLOAK_TOKEN_URL,
    OAUTH_REDIRECT_URI,
    OAUTH_SCOPE,
    REFRESH_COOKIE_NAME,
)

router = APIRouter(prefix="/auth", tags=["Авторизація"])


class ExchangeRequest(BaseModel):
    code: str = Field(min_length=1)
    code_verifier: str = Field(min_length=43, max_length=128)
    redirect_uri: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


def _set_refresh_cookie(response: Response, refresh_token: str, max_age: int | None = None) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/auth",
        max_age=max_age,
    )


async def _token_request(data: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            result = await client.post(KEYCLOAK_TOKEN_URL, data=data)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервер авторизації Keycloak недоступний.",
        ) from exc

    if not result.is_success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Keycloak відхилив запит на отримання токена.",
        )
    return result.json()


@router.get(
    "/config",
    summary="Отримати налаштування OAuth 2.0 + PKCE",
    description="Публічні параметри, які клієнтська частина використовує для початку потоку коду авторизації з PKCE (S256).",
)
def auth_config():
    query = urlencode(
        {
            "client_id": KEYCLOAK_CLIENT_ID,
            "redirect_uri": OAUTH_REDIRECT_URI,
            "response_type": "code",
            "scope": OAUTH_SCOPE,
            "code_challenge_method": "S256",
        }
    )
    return {
        "authorization_endpoint": KEYCLOAK_AUTHORIZE_URL,
        "authorization_url_template": f"{KEYCLOAK_AUTHORIZE_URL}?{query}",
        "client_id": KEYCLOAK_CLIENT_ID,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "scope": OAUTH_SCOPE,
        "code_challenge_method": "S256",
    }


@router.post(
    "/exchange",
    response_model=TokenResponse,
    summary="Обміняти код авторизації на токен доступу",
    description="Серверна частина обмінює код авторизації в Keycloak і повертає короткоживучий токен доступу. Токен оновлення зберігається у захищеному HttpOnly cookie-файлі.",
)
async def exchange_code(payload: ExchangeRequest, response: Response):
    if payload.redirect_uri != OAUTH_REDIRECT_URI:
        raise HTTPException(status_code=400, detail="Некоректний redirect URI.")

    token_data = await _token_request(
        {
            "grant_type": "authorization_code",
            "client_id": KEYCLOAK_CLIENT_ID,
            "code": payload.code,
            "redirect_uri": payload.redirect_uri,
            "code_verifier": payload.code_verifier,
        }
    )
    refresh_token = token_data.get("refresh_token")
    if refresh_token:
        _set_refresh_cookie(response, refresh_token, token_data.get("refresh_expires_in"))

    return {
        "access_token": token_data["access_token"],
        "token_type": token_data.get("token_type", "Bearer"),
        "expires_in": int(token_data.get("expires_in", 300)),
    }


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Оновити токен доступу",
    description="Використовує токен оновлення із захищеного HttpOnly cookie-файлу.",
)
async def refresh_access_token(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Сесію не знайдено. Увійдіть знову.")

    token_data = await _token_request(
        {
            "grant_type": "refresh_token",
            "client_id": KEYCLOAK_CLIENT_ID,
            "refresh_token": refresh_token,
        }
    )
    new_refresh = token_data.get("refresh_token")
    if new_refresh:
        _set_refresh_cookie(response, new_refresh, token_data.get("refresh_expires_in"))

    return {
        "access_token": token_data["access_token"],
        "token_type": token_data.get("token_type", "Bearer"),
        "expires_in": int(token_data.get("expires_in", 300)),
    }


@router.get(
    "/me",
    summary="Поточний користувач",
    description="Повертає ім'я користувача та ролі з перевіреного JWT-токена доступу.",
)
def me(user: CurrentUser = Depends(get_current_user)):
    return {
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "roles": user.roles,
        "primary_role": user.primary_role,
    }


@router.post(
    "/logout",
    summary="Завершити сесію",
    description="Завершує сесію оновлення в Keycloak та видаляє HttpOnly cookie-файл.",
)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    if refresh_token:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    KEYCLOAK_LOGOUT_URL,
                    data={
                        "client_id": KEYCLOAK_CLIENT_ID,
                        "refresh_token": refresh_token,
                    },
                )
        except httpx.HTTPError:
            pass
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/auth")
    return {"message": "Сесію завершено."}
