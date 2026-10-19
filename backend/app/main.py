from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.config import FRONTEND_URL
from app.routers.analytics import router as analytics_router
from app.routers.auth import router as auth_router
from app.routers.data import router as data_router
from app.routers.ml import router as ml_router

openapi_tags = [
    {"name": "Авторизація", "description": "OAuth 2.0, потік коду авторизації з PKCE, сесія та ролі користувачів."},
    {"name": "Аналітика", "description": "Історичний аналіз навантаження МРТ, КТ та рентгену."},
    {"name": "Прогнозування", "description": "Прогнозування навантаження методами машинного навчання та оцінка моделей."},
    {"name": "Дані", "description": "Завантаження, перевірка та перегляд набору даних. Доступ лише для адміністратора."},
    {"name": "Система", "description": "Службові перевірки стану API."},
]

app = FastAPI(
    title="Tower — API аналітики клініки",
    version="0.5.0",
    openapi_tags=openapi_tags,
    docs_url="/swagger",
    redoc_url=None,
    swagger_ui_parameters={"defaultModelsExpandDepth": -1, "displayRequestDuration": True, "docExpansion": "none"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Система"], summary="Інформація про API")
def root():
    return {
        "name": "Tower — API аналітики клініки",
        "status": "працює",
        "api_menu": "/docs",
        "technical_docs": "/swagger",
        "version": "0.5.0",
    }


@app.get("/docs", include_in_schema=False, response_class=HTMLResponse)
def api_menu():
    return """<!doctype html>
<html lang="uk">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Tower — меню API</title>
  <style>
    *{box-sizing:border-box} body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:#f4f7fb;color:#172033;margin:0}
    main{max-width:1050px;margin:42px auto;padding:0 22px} h1{margin:0 0 6px;font-size:30px}.sub{color:#667085;margin-bottom:26px}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}.card{background:#fff;border-radius:16px;padding:20px;box-shadow:0 8px 28px rgba(15,23,42,.06)}
    .card h2{font-size:18px;margin:0 0 12px}.row{margin:9px 0;line-height:1.45}code{background:#eef4ff;padding:3px 7px;border-radius:7px;color:#174ea6}
    .role{margin-top:14px;font-size:13px;color:#667085;border-top:1px solid #eef0f4;padding-top:10px}.links{margin-top:18px;background:#fff;border-radius:16px;padding:18px 20px;box-shadow:0 8px 28px rgba(15,23,42,.06)}
    a{color:#1677ff;text-decoration:none;font-weight:600}a:hover{text-decoration:underline}.badge{display:inline-block;background:#e6f4ff;color:#0958d9;border-radius:999px;padding:3px 9px;font-size:12px;margin-left:8px}
  </style>
</head>
<body><main>
  <h1>Tower — API аналітики клініки <span class="badge">v0.5.0</span></h1>
  <div class="sub">OAuth 2.0 + PKCE (S256) · ролі: адміністратор і менеджер</div>
  <div class="grid">
    <section class="card"><h2>Авторизація</h2>
      <div class="row"><code>GET /auth/config</code> — параметри входу через PKCE</div>
      <div class="row"><code>POST /auth/exchange</code> — обмін коду авторизації на токен доступу</div>
      <div class="row"><code>POST /auth/refresh</code> — оновлення токена доступу</div>
      <div class="row"><code>GET /auth/me</code> — поточний користувач і його роль</div>
      <div class="row"><code>POST /auth/logout</code> — завершення сесії</div>
      <div class="role">Вхід: Keycloak · Authorization Code + PKCE S256</div>
    </section>
    <section class="card"><h2>Аналітика</h2>
      <div class="row"><code>/analytics/summary</code> — зведена статистика</div>
      <div class="row"><code>/analytics/trends</code> — тренди та ковзні середні</div>
      <div class="row"><code>/analytics/seasonality</code> — сезонність</div>
      <div class="row"><code>/analytics/anomalies</code> — аномальні дні</div>
      <div class="row"><code>/analytics/holiday-impact</code> — вплив календарних свят</div>
      <div class="role">Доступ: менеджер та адміністратор</div>
    </section>
    <section class="card"><h2>Прогнозування</h2>
      <div class="row"><code>GET /ml/forecast</code> — прогноз МРТ, КТ, рентгену та загального навантаження</div>
      <div class="row"><code>POST /ml/train</code> — навчання й вибір моделей</div>
      <div class="row"><code>GET /ml/performance</code> — метрики якості</div>
      <div class="row"><code>GET /ml/backtest</code> — хронологічне тестування</div>
      <div class="role">Прогноз: менеджер / адміністратор · навчання та метрики: лише адміністратор</div>
    </section>
    <section class="card"><h2>Дані</h2>
      <div class="row"><code>GET /data/info</code> — стан набору даних</div>
      <div class="row"><code>GET /data/preview</code> — останні записи</div>
      <div class="row"><code>POST /data/upload</code> — завантаження CSV/XLSX</div>
      <div class="role">Доступ: лише адміністратор</div>
    </section>
  </div>
  <div class="links"><a href="/swagger">Технічна інтерактивна документація</a> · <a href="/openapi.json">Схема OpenAPI (JSON)</a></div>
</main></body></html>"""


@app.get("/health", tags=["Система"], summary="Перевірити стан API")
def health():
    return {"status": "працює"}


app.include_router(auth_router)
app.include_router(analytics_router)
app.include_router(data_router)
app.include_router(ml_router)
