# Tower Frontend v5

React + TypeScript + Ant Design + Recharts.

У стандартному режимі frontend запускається через Docker Compose з кореня проєкту:

```powershell
docker compose up -d
```

Адреса:

```text
http://localhost:3000
```

Папка `frontend/src` підключена до контейнера як volume, тому зміни компонентів автоматично оновлюються через Vite HMR.

Після зміни `package.json` або Dockerfile потрібно перебудувати frontend:

```powershell
docker compose up -d --build frontend
```

Інтерфейс українською. Доступ за ролями:

- менеджер: Панель / Аналітика / Прогноз;
- адміністратор: додатково Дані / Моделі.

Авторизація починається у браузері через PKCE S256, а обмін authorization code на токени виконує FastAPI backend.
