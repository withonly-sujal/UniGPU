from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models.user import User
from app.models.gpu import GPU, GPUStatus
from app.schemas.gpu import GPUCreate, GPUOut, GPUStatusUpdate
from app.services.connection_manager import manager

router = APIRouter()


@router.post("/register", response_model=GPUOut, status_code=status.HTTP_201_CREATED)
async def register_gpu(
    data: GPUCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("provider", "admin")),
):
    gpu = GPU(
        provider_id=current_user.id,
        name=data.name,
        vram_mb=data.vram_mb,
        cuda_version=data.cuda_version,
        status=GPUStatus.offline,
    )
    db.add(gpu)
    await db.flush()
    return gpu


@router.get("/", response_model=List[GPUOut])
async def list_gpus(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GPU))
    return result.scalars().all()


@router.get("/available", response_model=List[GPUOut])
async def list_available_gpus(
    min_vram: int = 0,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GPU)
        .where(GPU.status == GPUStatus.online, GPU.vram_mb >= min_vram)
        .order_by(GPU.vram_mb.asc())
    )
    return result.scalars().all()


@router.patch("/{gpu_id}/status", response_model=GPUOut)
async def update_gpu_status(
    gpu_id: str,
    data: GPUStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("provider", "admin")),
):
    result = await db.execute(select(GPU).where(GPU.id == gpu_id))
    gpu = result.scalar_one_or_none()
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU not found")
    if gpu.provider_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Not your GPU")
    gpu.status = data.status
    await db.flush()

    # Send stop command to agent via WebSocket when going offline
    if data.status == "offline" and manager.is_connected(gpu_id):
        await manager.send_to_gpu(gpu_id, {"type": "control", "action": "stop"})

    return gpu
