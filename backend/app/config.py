from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent.parent
if load_dotenv is not None:
    load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"
DATA_FILE = DATA_DIR / "clinic_visits.csv"
MODEL_FILE = MODEL_DIR / "attendance_models.joblib"
METADATA_FILE = MODEL_DIR / "attendance_model_metadata.json"
BACKTEST_FILE = MODEL_DIR / "attendance_model_backtest.json"

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")

# Public URL is used in browser redirects and as the expected JWT issuer.
KEYCLOAK_PUBLIC_URL = os.getenv(
    "KEYCLOAK_PUBLIC_URL",
    os.getenv("KEYCLOAK_BASE_URL", "http://localhost:8080"),
).rstrip("/")

# Internal URL is used by FastAPI when it runs inside Docker Compose.
# Outside Docker it can simply be identical to KEYCLOAK_PUBLIC_URL.
KEYCLOAK_INTERNAL_URL = os.getenv("KEYCLOAK_INTERNAL_URL", KEYCLOAK_PUBLIC_URL).rstrip("/")

KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "tower")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "tower-web")

KEYCLOAK_ISSUER = f"{KEYCLOAK_PUBLIC_URL}/realms/{KEYCLOAK_REALM}"
KEYCLOAK_AUTHORIZE_URL = f"{KEYCLOAK_PUBLIC_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/auth"
KEYCLOAK_TOKEN_URL = f"{KEYCLOAK_INTERNAL_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
KEYCLOAK_LOGOUT_URL = f"{KEYCLOAK_INTERNAL_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/logout"
KEYCLOAK_JWKS_URL = f"{KEYCLOAK_INTERNAL_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"

OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", f"{FRONTEND_URL}/auth/callback")
OAUTH_SCOPE = "openid profile email"
REFRESH_COOKIE_NAME = "tower_refresh_token"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}
