# ─────────────────────────────────────────────────
# UniGPU GPU Agent — Dockerfile
# ─────────────────────────────────────────────────
# This is a reference Dockerfile for containerised deployment.
# The agent is typically run natively on student machines.
# ─────────────────────────────────────────────────

FROM python:3.11-slim

# System deps for Docker-in-Docker communication
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent source
COPY . .

# Create default work directory
RUN mkdir -p /app/workdir

# Environment defaults
ENV BACKEND_WS_URL=ws://host.docker.internal:8000/ws/agent
ENV BACKEND_HTTP_URL=http://host.docker.internal:8000
ENV WORK_DIR=/app/workdir

# Entry point
CMD ["python", "agent.py"]
