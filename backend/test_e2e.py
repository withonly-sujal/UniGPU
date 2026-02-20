"""
UniGPU — Full End-to-End Integration Test
Registers users, GPU, starts agent inline, submits job, polls until done.
"""
import httpx
import time

BASE = "http://localhost:8000"
c = httpx.Client(base_url=BASE, timeout=15)

print("=" * 55)
print("  UniGPU — End-to-End Integration Test")
print("=" * 55)

# ── Setup: Users + GPU ─────────────────────────────
print("\n[1] Setting up test data...")

# Provider
c.post("/auth/register", json={"email": "e2e_p@t.com", "username": "e2e_p", "password": "pw", "role": "provider"})
r = c.post("/auth/login", json={"username": "e2e_p", "password": "pw"})
pt = r.json()["access_token"]
ph = {"Authorization": f"Bearer {pt}"}

# Register GPU
r = c.post("/gpus/register", json={"name": "E2E-TestGPU", "vram_mb": 8192, "cuda_version": "12.0"}, headers=ph)
gpu_id = r.json()["id"]
print(f"    GPU registered: {gpu_id}")

# Client
c.post("/auth/register", json={"email": "e2e_c@t.com", "username": "e2e_c", "password": "pw", "role": "client"})
r = c.post("/auth/login", json={"username": "e2e_c", "password": "pw"})
ct = r.json()["access_token"]
ch = {"Authorization": f"Bearer {ct}"}
c.post("/wallet/topup", json={"amount": 100}, headers=ch)
print("    Client created and wallet topped up")

# Write GPU ID to agent .env
print(f"    Writing agent .env with GPU_ID={gpu_id}")
with open("../agent/.env", "w") as f:
    f.write(f"""GPU_ID={gpu_id}
BACKEND_WS_URL=ws://localhost:8000/ws/agent
BACKEND_HTTP_URL=http://localhost:8000
AGENT_TOKEN=
HEARTBEAT_INTERVAL=10
WORK_DIR=./jobs
DOCKER_BASE_IMAGE=python:3.11-slim
MAX_JOB_TIMEOUT=600
""")

# ── Wait for agent to connect ────────────────────────
print("\n[2] Please start the agent in another terminal:")
print("    cd d:\\UniGPU\\agent")
print("    d:\\UniGPU\\venv\\Scripts\\python.exe agent.py")
print("\n    Waiting for agent to connect...")

for i in range(60):
    time.sleep(2)
    r = c.get("/gpus/", headers=ph)
    gpus = r.json()
    e2e_gpu = next((g for g in gpus if g["id"] == gpu_id), None)
    if e2e_gpu and e2e_gpu["status"] == "online":
        print(f"    Agent connected! GPU status: online")
        break
    if i % 5 == 0:
        print(f"    ...waiting ({i*2}s)")
else:
    print("    TIMEOUT: Agent did not connect within 120s")
    exit(1)

# ── Submit Job ──────────────────────────────────────
print("\n[3] Submitting training job...")

script = b"""import time
print("=== UniGPU E2E Test ===")
for i in range(1, 4):
    time.sleep(1)
    print(f"Epoch {i}/3 complete")
print("Done!")
"""

r = c.post("/jobs/submit", files={"script": ("train.py", script)}, headers=ch)
assert r.status_code == 201, f"Submit failed: {r.status_code} {r.text}"
job = r.json()
print(f"    Job ID: {job['id']}")
print(f"    Status: {job['status']}")

# ── Poll ────────────────────────────────────────────
print("\n[4] Polling job status...")
final = "unknown"
for i in range(40):
    time.sleep(3)
    r = c.get(f"/jobs/{job['id']}", headers=ch)
    s = r.json()["status"]
    print(f"    {(i+1)*3:3d}s — {s}")
    if s in ("completed", "failed", "error"):
        final = s
        break
    final = s

# ── Logs ────────────────────────────────────────────
r = c.get(f"/jobs/{job['id']}/logs", headers=ch)
logs = r.json().get("logs", "")
print(f"\n[5] Job Logs:\n{'─' * 40}")
print(logs if logs else "(no logs)")
print("─" * 40)

# ── Result ──────────────────────────────────────────
print(f"\n{'=' * 55}")
if final == "completed":
    print("  ✅ SUCCESS — Full pipeline works end-to-end!")
elif final == "queued":
    print("  ⏳ Job was dispatched to agent but not yet finished")
elif final == "pending":
    print("  ❌ Job stayed pending — dispatch may not have worked")
else:
    print(f"  ⚠️  Job ended with: {final}")
print("=" * 55)
