import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select

from app.database import async_session
from app.models.gpu import GPU, GPUStatus
from app.models.job import Job, JobStatus
from app.services.connection_manager import manager
from app.services.billing import charge_client

router = APIRouter()


@router.websocket("/ws/agent/{gpu_id}")
async def agent_websocket(websocket: WebSocket, gpu_id: str):
    """WebSocket endpoint for GPU agents.

    Protocol messages (JSON):
      Agent → Server:
        {"type": "heartbeat"}
        {"type": "job_status", "job_id": "...", "status": "running|completed|failed"}
        {"type": "log", "job_id": "...", "data": "..."}
        {"type": "metrics", "data": {...}}
        {"type": "agent_log", "data": "..."}

      Server → Agent:
        {"type": "assign_job", "job_id": "...", "script_url": "/jobs/.../download/...", "requirements_url": "..."|null}
    """
    # Optional: validate token via query param (token = websocket.query_params.get("token"))
    await manager.connect(gpu_id, websocket)
    print(f"🔌 GPU agent connected: {gpu_id}")

    # Mark GPU as online and cache the provider mapping
    async with async_session() as db:
        result = await db.execute(select(GPU).where(GPU.id == gpu_id))
        gpu = result.scalar_one_or_none()
        if gpu:
            gpu.status = GPUStatus.online
            gpu.last_heartbeat = datetime.now(timezone.utc)
            await db.commit()
            # Cache gpu_id → provider_id for fast relay
            manager.set_gpu_provider(gpu_id, gpu.provider_id)

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "heartbeat":
                async with async_session() as db:
                    result = await db.execute(select(GPU).where(GPU.id == gpu_id))
                    gpu = result.scalar_one_or_none()
                    if gpu:
                        gpu.last_heartbeat = datetime.now(timezone.utc)
                        await db.commit()

                # Relay metrics if included in heartbeat
                metrics = msg.get("metrics")
                if metrics:
                    provider_id = manager.get_provider_for_gpu(gpu_id)
                    if provider_id:
                        await manager.send_to_provider(provider_id, {
                            "type": "metrics",
                            "gpu_id": gpu_id,
                            "data": metrics,
                        })

            elif msg_type == "job_status":
                job_id = msg.get("job_id")
                new_status = msg.get("status")
                async with async_session() as db:
                    result = await db.execute(select(Job).where(Job.id == job_id))
                    job = result.scalar_one_or_none()
                    if job:
                        if new_status == "running":
                            job.status = JobStatus.running
                            job.started_at = datetime.now(timezone.utc)
                        elif new_status == "completed":
                            job.status = JobStatus.completed
                            job.completed_at = datetime.now(timezone.utc)
                            # Bill the client
                            await charge_client(db, job)
                            # Free the GPU
                            gpu_result = await db.execute(select(GPU).where(GPU.id == gpu_id))
                            gpu = gpu_result.scalar_one_or_none()
                            if gpu:
                                gpu.status = GPUStatus.online
                        elif new_status == "failed":
                            job.status = JobStatus.failed
                            job.completed_at = datetime.now(timezone.utc)
                            gpu_result = await db.execute(select(GPU).where(GPU.id == gpu_id))
                            gpu = gpu_result.scalar_one_or_none()
                            if gpu:
                                gpu.status = GPUStatus.online
                        await db.commit()

                # Relay job status to provider dashboard
                provider_id = manager.get_provider_for_gpu(gpu_id)
                if provider_id:
                    await manager.send_to_provider(provider_id, {
                        "type": "job_status",
                        "gpu_id": gpu_id,
                        "job_id": job_id,
                        "status": new_status,
                    })

            elif msg_type == "log":
                job_id = msg.get("job_id")
                log_data = msg.get("data", "")
                async with async_session() as db:
                    result = await db.execute(select(Job).where(Job.id == job_id))
                    job = result.scalar_one_or_none()
                    if job:
                        job.logs = (job.logs or "") + log_data + "\n"
                        await db.commit()

                # Relay job logs to provider dashboard
                provider_id = manager.get_provider_for_gpu(gpu_id)
                if provider_id:
                    await manager.send_to_provider(provider_id, {
                        "type": "job_log",
                        "gpu_id": gpu_id,
                        "job_id": job_id,
                        "data": log_data,
                    })

            elif msg_type == "metrics":
                # System metrics from agent (GPU temp, CPU, RAM, etc.)
                provider_id = manager.get_provider_for_gpu(gpu_id)
                if provider_id:
                    await manager.send_to_provider(provider_id, {
                        "type": "metrics",
                        "gpu_id": gpu_id,
                        "data": msg.get("data", {}),
                    })

            elif msg_type == "agent_log":
                # Agent's own Python log lines
                provider_id = manager.get_provider_for_gpu(gpu_id)
                if provider_id:
                    await manager.send_to_provider(provider_id, {
                        "type": "agent_log",
                        "gpu_id": gpu_id,
                        "data": msg.get("data", ""),
                    })

    except WebSocketDisconnect:
        manager.disconnect(gpu_id)
        print(f"🔌 GPU agent disconnected: {gpu_id}")
        # Mark GPU as offline
        async with async_session() as db:
            result = await db.execute(select(GPU).where(GPU.id == gpu_id))
            gpu = result.scalar_one_or_none()
            if gpu:
                gpu.status = GPUStatus.offline
                await db.commit()

        # Notify provider dashboard
        provider_id = manager.get_provider_for_gpu(gpu_id)
        if provider_id:
            await manager.send_to_provider(provider_id, {
                "type": "agent_status",
                "gpu_id": gpu_id,
                "status": "disconnected",
            })


@router.websocket("/ws/provider/{provider_id}")
async def provider_websocket(websocket: WebSocket, provider_id: str):
    """WebSocket endpoint for provider dashboards.

    The provider connects here to receive real-time updates about their GPUs:
      - metrics:      {"type": "metrics", "gpu_id": "...", "data": {...}}
      - agent_log:    {"type": "agent_log", "gpu_id": "...", "data": "..."}
      - job_log:      {"type": "job_log", "gpu_id": "...", "job_id": "...", "data": "..."}
      - job_status:   {"type": "job_status", "gpu_id": "...", "job_id": "...", "status": "..."}
      - agent_status: {"type": "agent_status", "gpu_id": "...", "status": "disconnected"}
    """
    await manager.connect_provider(provider_id, websocket)
    print(f"📊 Provider dashboard connected: {provider_id}")

    try:
        # Keep the connection alive — the provider mostly listens
        while True:
            # Provider can send pings or control messages if needed
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            # Currently no provider→server messages are expected
            # but we keep the loop to detect disconnects
    except WebSocketDisconnect:
        manager.disconnect_provider(provider_id, websocket)
        print(f"📊 Provider dashboard disconnected: {provider_id}")
