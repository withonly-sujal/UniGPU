import os
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.deps import get_current_user, require_role
from app.config import get_settings
from app.models.user import User
from app.models.job import Job, JobStatus
from app.models.gpu import GPU, GPUStatus
from app.schemas.job import JobOut

router = APIRouter()
settings = get_settings()


async def _save_upload(file: UploadFile, job_id: str, filename: str) -> str:
    """Save an uploaded file to uploads/<job_id>/<filename>."""
    job_dir = os.path.join(settings.UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    path = os.path.join(job_dir, filename)
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    return path


@router.post("/submit", response_model=JobOut, status_code=status.HTTP_201_CREATED)
async def submit_job(
    script: UploadFile = File(...),
    requirements: UploadFile | None = File(None),
    gpu_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("client", "admin")),
):
    job_id = str(uuid.uuid4())

    # Save files
    script_path = await _save_upload(script, job_id, script.filename)
    req_path = None
    if requirements:
        req_path = await _save_upload(requirements, job_id, requirements.filename)

    job = Job(
        id=job_id,
        client_id=current_user.id,
        script_path=script_path,
        requirements_path=req_path,
        status=JobStatus.pending,
    )
    db.add(job)
    await db.flush()

    # Try to match with a GPU and dispatch
    from app.services.matching import find_available_gpu
    from app.services.connection_manager import manager
    from pathlib import Path

    gpu = None
    if gpu_id:
        # Client selected a specific GPU
        result = await db.execute(
            select(GPU).where(GPU.id == gpu_id, GPU.status == GPUStatus.online)
        )
        gpu = result.scalar_one_or_none()
        if not gpu:
            # Requested GPU isn't available — fall back to auto-match
            gpu = await find_available_gpu(db, min_vram=0)
    else:
        gpu = await find_available_gpu(db, min_vram=0)

    if gpu and manager.is_connected(gpu.id):
        # Assign GPU to job
        job.gpu_id = gpu.id
        job.status = JobStatus.queued
        gpu.status = GPUStatus.busy

        # Build download URLs
        script_name = Path(script_path).name
        script_url = f"/jobs/{job_id}/download/{script_name}"
        req_url = None
        if req_path:
            req_name = Path(req_path).name
            req_url = f"/jobs/{job_id}/download/{req_name}"

        await db.commit()

        # Send assign_job via WebSocket
        await manager.send_to_gpu(gpu.id, {
            "type": "assign_job",
            "job_id": job_id,
            "script_url": script_url,
            "requirements_url": req_url,
        })
    else:
        await db.commit()

    return job


@router.get("/", response_model=List[JobOut])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.value == "admin":
        result = await db.execute(select(Job).order_by(Job.created_at.desc()))
    else:
        result = await db.execute(
            select(Job).where(Job.client_id == current_user.id).order_by(Job.created_at.desc())
        )
    return result.scalars().all()


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if current_user.role.value != "admin" and job.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return job


@router.get("/{job_id}/logs")
async def get_job_logs(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if current_user.role.value != "admin" and job.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return {"job_id": job.id, "logs": job.logs or ""}


@router.get("/{job_id}/download/{filename}")
async def download_job_file(job_id: str, filename: str):
    """Download a job file (script or requirements).

    Used by GPU agents to fetch job files over HTTP.
    No auth required — job UUID is unguessable.
    """
    # Sanitise filename to prevent path traversal
    safe_name = Path(filename).name
    file_path = Path(settings.UPLOAD_DIR) / job_id / safe_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(file_path),
        filename=safe_name,
        media_type="application/octet-stream",
    )


@router.post("/{job_id}/cancel", response_model=JobOut)
async def cancel_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a pending, queued, or running job."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if current_user.role.value != "admin" and job.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if job.status.value in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Job already {job.status.value}")

    # If the job is running on a GPU, tell the agent to stop it
    if job.gpu_id and job.status in (JobStatus.running, JobStatus.queued):
        from app.services.connection_manager import manager

        if manager.is_connected(job.gpu_id):
            await manager.send_to_gpu(job.gpu_id, {
                "type": "cancel_job",
                "job_id": job.id,
            })

        # Free up the GPU
        gpu_result = await db.execute(select(GPU).where(GPU.id == job.gpu_id))
        gpu = gpu_result.scalar_one_or_none()
        if gpu and gpu.status == GPUStatus.busy:
            gpu.status = GPUStatus.online

    job.status = JobStatus.cancelled
    job.completed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    await db.commit()
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a completed, failed, or cancelled job."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if current_user.role.value != "admin" and job.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if job.status.value in ("queued", "running"):
        raise HTTPException(status_code=400, detail="Stop the job before deleting it")

    # Clean up uploaded files
    import shutil
    job_dir = os.path.join(settings.UPLOAD_DIR, job_id)
    if os.path.isdir(job_dir):
        shutil.rmtree(job_dir, ignore_errors=True)

    await db.delete(job)
    await db.commit()
