# Tower Backend v5

FastAPI backend для Tower.

Основні групи API:

- `/auth/*` — OAuth 2.0 Authorization Code + PKCE, refresh через HttpOnly cookie;
- `/analytics/*` — аналітика для менеджера й адміністратора;
- `/ml/forecast` — прогноз для менеджера й адміністратора;
- `/data/*`, `/ml/train`, `/ml/performance`, `/ml/backtest` — лише адміністратор.

У стандартному режимі backend запускається контейнером через `docker compose up -d` з кореня проєкту.

Код `backend/app` підключено як volume, тому зміни Python-коду автоматично підхоплюються Uvicorn `--reload` без перебудови образу.

Після зміни `requirements.txt` виконайте:

```powershell
docker compose up -d --build backend
```

Адреси:

- українське меню API: `http://localhost:8000/docs`;
- технічний Swagger: `http://localhost:8000/swagger`.

Для запуску backend без Docker дивіться кореневий `README.md` або використовуйте стандартний локальний Uvicorn workflow.
