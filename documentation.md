# UniGPU — Team Documentation

> Peer-to-Peer GPU Sharing Platform for Students

---

## Architecture Overview

```
┌─────────────┐     REST API      ┌──────────────────────────────────┐
│   Frontend   │ ◄──────────────► │         Backend (Docker)          │
│  Vite+React  │   localhost:5173  │                                  │
│  :5173       │                   │  FastAPI (:8000)                 │
└─────────────┘     WebSocket     │  PostgreSQL (:5432)              │
                                   │  Redis (:6379)                   │
┌─────────────┐  ◄──────────────► │  Celery Worker (job matching)    │
│  GPU Agent   │   ws://...:8000   └──────────────────────────────────┘
│  (Python)    │
│  Student PC  │
└─────────────┘
```

**Three Roles:**
- **Client** — Submits training jobs, manages wallet
- **Provider** — Shares GPU, runs agent, earns credits
- **Admin** — Monitors platform, views all data

---

## Prerequisites

- **Docker Desktop** — [download](https://www.docker.com/products/docker-desktop/)
- **Node.js 18+** — [download](https://nodejs.org/)
- **Python 3.10+** — [download](https://www.python.org/)
- **Git**

---

## Quick Start

### 1. Start Backend (Docker)

```powershell
cd d:\UniGPU
$env:PATH += ";C:\Program Files\Docker\Docker\resources\bin"
docker compose up --build
```

This starts 4 containers: PostgreSQL, Redis, FastAPI backend, Celery worker.

### 2. Start Frontend

```powershell
cd d:\UniGPU\frontend
npm install          # first time only
npm run dev
```

Opens at **http://localhost:5173**

### 3. Start GPU Agent (optional)

```powershell
cd d:\UniGPU\agent
pip install -r requirements.txt    # first time only
python agent.py
```

---

## Common Commands

| Action | Command |
|---|---|
| **Start backend** | `docker compose up --build` |
| **Start backend (background)** | `docker compose up --build -d` |
| **Stop backend** | `docker compose down` |
| **Stop + wipe database** | `docker compose down -v` |
| **View logs (all)** | `docker compose logs -f` |
| **View logs (backend only)** | `docker compose logs backend -f` |
| **View logs (celery only)** | `docker compose logs celery-worker -f` |
| **Start frontend** | `cd frontend && npm run dev` |
| **Run API tests** | `cd backend && python test_api.py` |
| **Start agent** | `cd agent && python agent.py` |

> **Note:** On Windows, you may need to add Docker to PATH first:  
> `$env:PATH += ";C:\Program Files\Docker\Docker\resources\bin"`

---

## Credentials

### Database (PostgreSQL via DBeaver / pgAdmin)

| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | **`unigpu`** |
| Username | `unigpu` |
| Password | `unigpu_secret` |

### Frontend Test Accounts

| Role | Username | Password |
|---|---|---|
| Client | `testclient` | `pass123` |
| Provider | `testprovider` | `pass123` |
| Admin | `testadmin` | `pass123` |

> These accounts are created by `test_api.py`. If database was wiped (`docker compose down -v`), run the test script again to recreate them.

---

## Monitoring & Debugging

| What | Where |
|---|---|
| **Docker containers & logs** | Docker Desktop app |
| **Database tables** | DBeaver (credentials above) |
| **API docs / testing** | http://localhost:8000/docs (Swagger UI) |
| **Frontend** | http://localhost:5173 |
| **Backend health** | `GET http://localhost:8000/` |

### Key Database Tables

| Table | Contents |
|---|---|
| `users` | All registered users (id, username, email, role, password hash) |
| `gpus` | Registered GPUs (name, vram, cuda, status, last_heartbeat) |
| `jobs` | Submitted jobs (status, script_path, client_id, gpu_id, logs) |
| `wallets` | User balances |
| `transactions` | Credit/debit history |

---

## API Endpoints

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Register (email, username, password, role) |
| POST | `/auth/login` | Login → returns JWT token |

### GPUs
| Method | Endpoint | Description |
|---|---|---|
| GET | `/gpus/` | List all GPUs |
| GET | `/gpus/available` | List online GPUs |
| POST | `/gpus/register` | Register GPU (provider only) |
| PATCH | `/gpus/{id}/status` | Set GPU online/offline |

### Jobs
| Method | Endpoint | Description |
|---|---|---|
| POST | `/jobs/submit` | Upload script + requirements |
| GET | `/jobs/` | List user's jobs |
| GET | `/jobs/{id}` | Get job details |
| GET | `/jobs/{id}/logs` | Get job logs |
| GET | `/jobs/{id}/download/{filename}` | Download job file (used by agent) |

### Wallet
| Method | Endpoint | Description |
|---|---|---|
| GET | `/wallet/` | Get balance |
| POST | `/wallet/topup` | Add credits |
| GET | `/wallet/transactions` | Transaction history |

### Admin
| Method | Endpoint | Description |
|---|---|---|
| GET | `/admin/stats` | Platform stats |
| GET | `/admin/gpus` | All GPUs |
| GET | `/admin/jobs` | All jobs |
| GET | `/admin/users` | All users |

### WebSocket
| Endpoint | Description |
|---|---|
| `ws://localhost:8000/ws/agent/{gpu_id}` | GPU agent connection |

---

## Project Structure

```
UniGPU/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # App entry + CORS + routers
│   │   ├── config.py          # Settings (DB, Redis, JWT)
│   │   ├── database.py        # Async SQLAlchemy setup
│   │   ├── deps.py            # Auth dependencies
│   │   ├── models/            # SQLAlchemy models (user, gpu, job, wallet)
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── routers/           # API endpoints (auth, gpus, jobs, wallet, admin, ws)
│   │   ├── services/          # Business logic (billing, matching, connections)
│   │   └── worker/            # Celery tasks (job processing, heartbeat checks)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── test_api.py            # End-to-end API tests (31 tests)
│   └── .env
│
├── frontend/                   # Vite + React dashboard
│   └── src/
│       ├── api/client.js      # API wrapper
│       ├── context/AuthContext.jsx
│       ├── components/Sidebar.jsx
│       └── pages/             # Landing, Login, Register, 3 Dashboards
│
├── agent/                      # GPU agent (runs on student machines)
│   ├── agent.py               # Main orchestrator
│   ├── config.py              # Env-based config
│   ├── ws_client.py           # WebSocket client with auto-reconnect
│   ├── executor.py            # Docker job runner
│   ├── gpu_detector.py        # Detects local GPUs
│   ├── log_streamer.py        # Streams container logs to backend
│   ├── uploader.py            # Artifact upload (future)
│   └── .env                   # Agent config (GPU_ID, backend URL)
│
└── docker-compose.yml          # Backend stack (Postgres, Redis, API, Celery)
```

---

## Environment Variables

### Backend (`backend/.env`)
| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://unigpu:unigpu_secret@postgres:5432/unigpu` | DB connection |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key |

### Agent (`agent/.env`)
| Variable | Description |
|---|---|
| `GPU_ID` | GPU UUID from `POST /gpus/register` |
| `BACKEND_WS_URL` | `ws://localhost:8000/ws/agent` |
| `BACKEND_HTTP_URL` | `http://localhost:8000` |
| `HEARTBEAT_INTERVAL` | Seconds between heartbeats (default: 10) |
| `WORK_DIR` | Local job working directory |
| `DOCKER_BASE_IMAGE` | Docker image for jobs |

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `docker` not found | Add to PATH: `$env:PATH += ";C:\Program Files\Docker\Docker\resources\bin"` |
| Docker DNS error | Restart Docker Desktop, or retry (transient) |
| Registration fails (400) | Users already exist — this is normal on re-runs |
| Database empty after restart | Only if you used `docker compose down -v` — run `test_api.py` to recreate test data |
| DBeaver can't connect | Use database name `unigpu` (not `unigpu_db`) |
| Frontend CORS error | Backend already has `allow_origins=["*"]` — ensure backend is running |
| Agent can't connect | Check `GPU_ID` in agent `.env` matches a registered GPU |
