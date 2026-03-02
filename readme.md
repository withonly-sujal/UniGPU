<h1> You can donload the UniGPU Agent's .exe file from here 👉 <h1>
<p align="center">
  <h1 align="center">⬡ UniGPU</h1>
  <p align="center"><strong>Peer-to-Peer GPU Compute Marketplace — Built for Students, by Students</strong></p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
</p>

---

## 🚀 What is UniGPU?

UniGPU is a **peer-to-peer GPU sharing platform** that connects students who need compute power with students who have idle GPUs.

**The Problem:** High-performance GPUs are expensive and inaccessible to many students. Training ML models requires powerful hardware most individuals can't afford — yet thousands of student GPUs sit idle every day.

**The Solution:** UniGPU lets you **share your idle GPU and earn credits**, or **submit training jobs** that run on someone else's GPU. Every job is executed inside a **secure, isolated Docker container** with NVIDIA GPU runtime. The platform handles scheduling, execution, real-time log streaming, and usage-based billing — all automatically.

---

## 🏗️ Architecture

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

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Vite 7, React Router, FontAwesome, Cloudinary |
| **Backend API** | FastAPI (Python), async SQLAlchemy, Pydantic |
| **Database** | PostgreSQL 16 |
| **Cache / Broker** | Redis 7 |
| **Task Queue** | Celery (job matching, heartbeat monitoring) |
| **Auth** | JWT (jose), bcrypt password hashing |
| **Agent** | Python (websockets, docker SDK, pynvml, pystray) |
| **Job Isolation** | Docker containers with NVIDIA GPU runtime |
| **Infrastructure** | Docker Compose (4 services) |

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- [**Docker Desktop**](https://www.docker.com/products/docker-desktop/) — for running the backend stack
- [**Node.js 18+**](https://nodejs.org/) — for the frontend
- [**Python 3.10+**](https://www.python.org/) — for the GPU agent
- **Git**

---

## ⚡ Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/IammSwanand/UniGPU.git
cd UniGPU
```

### 2. Start the Backend

This spins up **4 Docker containers**: PostgreSQL, Redis, FastAPI, and Celery Worker.

```bash
docker compose up --build
```

> **Windows users:** If `docker` is not found, add Docker to PATH first:
> ```powershell
> $env:PATH += ";C:\Program Files\Docker\Docker\resources\bin"
> ```

Wait until you see the backend is ready (FastAPI logs will show `Uvicorn running on 0.0.0.0:8000`).

### 3. Start the Frontend

```bash
cd frontend
npm install        # first time only
npm run dev
```

The app opens at **http://localhost:5173**

### 4. Create an Account

Visit [http://localhost:5173/register](http://localhost:5173/register) and sign up as either a **Client** or **Provider**.

---

## 👤 Client Flow — Submit Training Jobs

As a **Client**, you want to run GPU-intensive workloads (ML training scripts) without owning a GPU.

1. **Register / Login** as a Client
2. **Top up your wallet** with credits from the Client Dashboard
3. **Upload your training script** (`.py` file) and optionally a `requirements.txt`
4. **Select a GPU** from the available GPUs list, or let the system auto-assign
5. **Submit the job** — it enters a queue and gets matched to an available GPU
6. **Monitor progress** — view real-time logs via the "📋 Logs" button
7. **Download logs** — once complete, click "⬇ Download" in the log viewer to save output as `.txt`
8. **Billing** — credits are deducted based on GPU usage time (₹0.002/second)

```
Client uploads script  →  Backend queues job  →  Celery matches to GPU
     →  Agent receives job  →  Runs in Docker  →  Streams logs  →  Done
```

---

## 🖥️ Provider Flow — Share Your GPU & Earn

As a **Provider**, you share your idle GPU with the network and earn credits for every job it runs.

1. **Register / Login** as a Provider
2. **Download the UniGPU Agent** from the [Download page](http://localhost:5173/download)
3. **Run the Agent** — double-click the `.exe`, the setup wizard guides you through:
   - Detecting your GPU hardware (name, VRAM, CUDA version)
   - Registering your GPU with the backend
   - Configuring the WebSocket connection
4. **Go Online** — your GPU appears in the marketplace and starts accepting jobs
5. **Monitor from Dashboard** — the Provider Dashboard shows:
   - GPU status & health metrics (utilization, temperature, memory)
   - Real-time agent logs
   - Earnings & transaction history
6. **Jobs run automatically** — the agent receives jobs, runs them in Docker containers, streams logs, and reports results
7. **Go Offline** anytime — toggle from the dashboard to pause accepting jobs

```
Agent starts  →  WebSocket connects  →  Heartbeats keep GPU "online"
     →  Job assigned  →  Docker container runs  →  Logs streamed  →  Credits earned
```

### Agent Requirements (Provider Machine)
- **NVIDIA GPU** with CUDA support
- **Docker Desktop** with NVIDIA Container Toolkit
- **Windows 10/11** (Linux/macOS coming soon)

---

## 📂 Project Structure

```
UniGPU/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # App entry + CORS + routers
│   │   ├── config.py          # Settings (DB, Redis, JWT)
│   │   ├── database.py        # Async SQLAlchemy setup
│   │   ├── deps.py            # Auth dependencies (JWT)
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── routers/           # API endpoints
│   │   │   ├── auth.py        # Register, Login
│   │   │   ├── gpus.py        # GPU registration & status
│   │   │   ├── jobs.py        # Job submission & management
│   │   │   ├── wallet.py      # Wallet & transactions
│   │   │   └── ws.py          # WebSocket for agent communication
│   │   └── services/          # Business logic
│   │       ├── billing.py     # Usage-based billing
│   │       ├── matching.py    # Job-to-GPU matching
│   │       └── connection_manager.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                   # Vite + React SPA
│   └── src/
│       ├── api/client.js      # API wrapper (Axios-like)
│       ├── context/           # Auth context (JWT storage)
│       ├── components/        # Shared components (Sidebar)
│       └── pages/             # Route pages
│           ├── Landing.jsx    # Homepage
│           ├── Login.jsx      # Authentication
│           ├── Register.jsx   # Account creation
│           ├── ClientDashboard.jsx    # Job submission & wallet
│           ├── ProviderDashboard.jsx  # GPU monitoring & earnings
│           ├── Download.jsx   # Agent download page
│           ├── AboutUs.jsx    # Team info
│           └── HowToUse.jsx   # User guide
│
└── docker-compose.yml          # Backend stack orchestration
```

---

## 🔌 API Reference

Full interactive API docs available at **http://localhost:8000/docs** (Swagger UI).

### Auth
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Register a new user |
| `POST` | `/auth/login` | Login → returns JWT token |

### GPUs
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/gpus/` | List all GPUs |
| `GET` | `/gpus/available` | List online GPUs |
| `POST` | `/gpus/register` | Register a GPU (provider) |
| `PATCH` | `/gpus/{id}/status` | Set GPU online/offline |

### Jobs
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/jobs/submit` | Upload script + requirements |
| `GET` | `/jobs/` | List user's jobs |
| `GET` | `/jobs/{id}/logs` | Get job logs |
| `DELETE` | `/jobs/{id}` | Delete a job |

### Wallet
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/wallet/` | Get balance |
| `POST` | `/wallet/topup` | Add credits |
| `GET` | `/wallet/transactions` | Transaction history |

### WebSocket
| Endpoint | Description |
|---|---|
| `ws://localhost:8000/ws/agent/{gpu_id}` | Real-time agent ↔ backend communication |

---

## 🧪 Common Commands

| Action | Command |
|---|---|
| Start backend | `docker compose up --build` |
| Start backend (detached) | `docker compose up --build -d` |
| Stop backend | `docker compose down` |
| Stop + wipe database | `docker compose down -v` |
| View backend logs | `docker compose logs backend -f` |
| Start frontend | `cd frontend && npm run dev` |
| Build frontend | `cd frontend && npm run build` |

---

## 🤝 Contributing

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/<your-username>/UniGPU.git`
3. **Create a branch**: `git checkout -b feature/your-feature`
4. **Set up the backend**: `docker compose up --build`
5. **Set up the frontend**: `cd frontend && npm install && npm run dev`
6. **Make your changes** and test locally
7. **Push** and open a **Pull Request**

---

## 📄 License

This project is proprietary software. All rights reserved.

Unauthorized copying, modification, distribution, or use of this software, in whole or in part, is strictly prohibited without explicit written permission from the authors.

---

## 👥 Credits

**UniGPU** is built with ❤️ by:

| | Name | Role | GitHub |
|---|---|---|---|
| 🧠 | **Swanand Wakadmane** | Co-founder & Developer | [@IammSwanand](https://github.com/IammSwanand) |
| 💻 | **Sujal Kadam** | Co-founder & Developer | [@withonly-sujal](https://github.com/withonly-sujal) |

> *AI & Data Science / Information Technology Engineering Undergraduates, Class of 2027*

---

<p align="center">
  <strong>⬡ UniGPU</strong> — Peer-to-Peer GPU Marketplace<br/>
  Built for Students · By Students<br/><br/>
  © 2026 UniGPU. All rights reserved.
</p>
