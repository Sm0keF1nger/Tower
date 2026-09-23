# Tower v5 — Dockerized clinic analytics & forecasting

**Tower** — повностекова вебсистема для аналізу та прогнозування щоденної кількості **МРТ, КТ і рентген-обстежень**.

У v5 усі основні компоненти запускаються через **Docker Compose**:

- Keycloak — OAuth 2.0 / OIDC + PKCE;
- FastAPI — backend, авторизація, аналітика та ML;
- React + Vite — frontend;
- локальні папки `backend/data` і `backend/models` залишаються на комп'ютері, тому набори даних та навчені моделі не губляться після перезапуску контейнера;
- дані Keycloak зберігаються у Docker volume.

> `backend/data/clinic_visits.csv` у комплекті — **синтетичний демонстраційний набір**. Для магістерської роботи його потрібно замінити реальними даними.

## Найпростіший запуск у Windows

### Перший запуск

1. Запустіть **Docker Desktop** і дочекайтеся стану `Engine running`.
2. Двічі натисніть:

```text
start-tower.bat
```

Під час першого запуску Docker автоматично завантажить/збере необхідні образи. Це може тривати кілька хвилин.

Після готовності автоматично відкриється:

```text
http://localhost:3000
```

Інші адреси:

```text
Tower:              http://localhost:3000
Українське меню API: http://localhost:8000/docs
Swagger:             http://localhost:8000/swagger
Keycloak:            http://localhost:8080
Keycloak Admin:      http://localhost:8080/admin
```

### Зупинка

Двічі натисніть:

```text
stop-tower.bat
```

Це зупиняє сервіси, але **не видаляє дані**.

### Стан сервісів

```text
status-tower.bat
```

### Логи

```text
logs-tower.bat
```

Для виходу з логів натисніть `Ctrl+C`.

## Коли потрібна перебудова Docker-образів

У development-режимі код підключений до контейнерів через volumes.

Тому після звичайних змін у:

```text
backend/app/**
frontend/src/**
```

**створювати новий контейнер не потрібно**:

- FastAPI перезавантажується автоматично;
- Vite оновлює frontend автоматично.

Перебудова потрібна, якщо змінено залежності або Docker-конфігурацію, наприклад:

```text
backend/requirements.txt
frontend/package.json
backend/Dockerfile
frontend/Dockerfile
docker-compose.yml
```

Тоді двічі натисніть:

```text
rebuild-tower.bat
```

або виконайте:

```powershell
docker compose up -d --build
```

Тобто **Docker не заважає додавати нові функції**. Ми можемо продовжувати робити v5.1, v5.2, v6 тощо у тих самих папках із кодом.

## Команди без `.bat`

У корені проєкту:

```powershell
docker compose up -d
```

Зупинити:

```powershell
docker compose stop
```

Перезапустити:

```powershell
docker compose restart
```

Перебудувати після зміни залежностей:

```powershell
docker compose up -d --build
```

Переглянути стан:

```powershell
docker compose ps
```

Логи:

```powershell
docker compose logs -f --tail=150
```

## Сервіси Docker Compose

```text
Docker Desktop
     │
     └── tower
          ├── keycloak :8080
          ├── backend  :8000
          └── frontend :3000
```

Backend звертається до Keycloak всередині Docker-мережі через:

```text
http://keycloak:8080
```

А браузер використовує публічну адресу:

```text
http://localhost:8080
```

Ці URL спеціально розділені у конфігурації, щоб OAuth 2.0 / PKCE коректно працював і з браузера, і між контейнерами.

## Збереження даних

### Клінічні дані

Папка:

```text
backend/data/
```

підключена до backend-контейнера. Завантажений CSV/XLSX та резервні копії залишаються на комп'ютері.

### ML-моделі

Папка:

```text
backend/models/
```

також підключена до контейнера. Перенавчені моделі не зникають після його перезапуску.

### Keycloak

Keycloak використовує named volume:

```text
keycloak_data
```

Тому користувачі, ролі та інші зміни зберігаються між запусками.

Якщо потрібно **повністю скинути локальний Keycloak** та знову імпортувати початковий realm, використовуйте:

```text
reset-keycloak-data.bat
```

> Ця дія видаляє зміни, які були вручну внесені у Keycloak після першого запуску.

## Демонстраційні користувачі

### Адміністратор

```text
логін: admin
пароль: Admin123!
```

Має доступ до:

- Панелі;
- Аналітики;
- Прогнозу;
- Даних;
- Моделей і перенавчання.

### Менеджер

```text
логін: manager
пароль: Manager123!
```

Має доступ лише до:

- Панелі;
- Аналітики;
- Прогнозу.

Backend також перевіряє ролі: приховування сторінок у frontend не є єдиним захистом.

### Адміністратор Keycloak

```text
логін: kcadmin
пароль: kcadmin
```

> Усі демонстраційні паролі призначені лише для локальної розробки.

## Формат даних

Рекомендований формат:

```csv
date,mri,ct,xray
2025-01-01,18,27,39
2025-01-02,21,31,35
```

Також підтримується довгий формат:

```csv
date,modality,patients
2025-01-01,mri,18
2025-01-01,ct,27
2025-01-01,xray,39
```

Tower не створює штучний розподіл МРТ/КТ/рентгену з одного загального показника `patients`.

## ML

Для МРТ, КТ і рентгену окремо порівнюються:

- лінійна регресія;
- Random Forest;
- Gradient Boosting;
- тижневий naive baseline.

Використовуються календарні, лагові та rolling-ознаки, зокрема:

- день тижня;
- місяць;
- тиждень року;
- `lag_1`, `lag_7`, `lag_14`;
- rolling average 7 / 14 / 30 днів;
- вихідний;
- календарне свято/значуща дата;
- день до/після календарної події;
- відстань до найближчої календарної події.

Моделі зі святковими ознаками порівнюються з варіантами без них за часовою валідацією.

## OAuth 2.0 + PKCE

```text
React
  │ створює code_verifier + S256 code_challenge + state
  ▼
Keycloak /authorize
  │ authorization code
  ▼
FastAPI /auth/exchange
  │ code + code_verifier
  ▼
Keycloak /token
  │
  ├─ access token → React
  └─ refresh token → HttpOnly cookie

React → Bearer access token → FastAPI
FastAPI → JWT signature + issuer/client + role validation
```

## Структура v5

```text
tower_project_v5/
├── backend/
│   ├── app/
│   ├── data/
│   ├── keycloak/
│   ├── models/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── start-tower.bat
├── stop-tower.bat
├── rebuild-tower.bat
├── logs-tower.bat
├── status-tower.bat
└── reset-keycloak-data.bat
```

## Важливо для production

Поточна конфігурація — **development/demo**. Для реального розгортання потрібно окремо налаштувати HTTPS, сильні секрети, production Keycloak, production frontend build та відповідну БД/сховище.
