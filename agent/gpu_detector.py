"""
UniGPU Agent — GPU Detection
Detects local GPU hardware via nvidia-smi. Falls back to mock data for dev/testing.
"""

import logging
import subprocess
import shutil
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

logger = logging.getLogger("unigpu.agent.gpu_detector")


@dataclass
class GPUInfo:
    """Detected GPU details."""
    index: int
    name: str
    vram_mb: int
    cuda_version: str
    driver_version: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _parse_nvidia_smi_output(raw: str) -> List[GPUInfo]:
    """Parse CSV output from nvidia-smi."""
    gpus: List[GPUInfo] = []
    for idx, line in enumerate(raw.strip().splitlines()):
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        gpus.append(GPUInfo(
            index=idx,
            name=parts[0],
            vram_mb=int(float(parts[1])),
            cuda_version="",       # filled separately
            driver_version=parts[2],
        ))
    return gpus


def _get_cuda_version() -> str:
    """Extract CUDA version from nvidia-smi header."""
    try:
        result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.splitlines():
            if "CUDA Version" in line:
                # e.g. "| NVIDIA-SMI 535.129.03   Driver Version: 535.129.03   CUDA Version: 12.2 |"
                part = line.split("CUDA Version:")[1]
                return part.strip().rstrip("|").strip()
    except Exception:
        pass
    return "unknown"


def detect_gpus() -> List[Dict[str, Any]]:
    """
    Detect GPUs on this machine.
    Returns a list of GPU info dicts. Falls back to a mock GPU if nvidia-smi is unavailable.
    """
    if not shutil.which("nvidia-smi"):
        logger.warning("nvidia-smi not found — returning mock GPU data (dev mode)")
        return [_mock_gpu()]

    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True, text=True, timeout=10,
        )

        if result.returncode != 0:
            logger.error("nvidia-smi failed: %s", result.stderr)
            return [_mock_gpu()]

        gpus = _parse_nvidia_smi_output(result.stdout)
        cuda_ver = _get_cuda_version()
        for gpu in gpus:
            gpu.cuda_version = cuda_ver

        logger.info("Detected %d GPU(s): %s", len(gpus), [g.name for g in gpus])
        return [g.to_dict() for g in gpus]

    except subprocess.TimeoutExpired:
        logger.error("nvidia-smi timed out")
        return [_mock_gpu()]
    except Exception as exc:
        logger.error("GPU detection failed: %s", exc)
        return [_mock_gpu()]


def _mock_gpu() -> Dict[str, Any]:
    """Return a mock GPU payload for development/testing on non-GPU machines."""
    return GPUInfo(
        index=0,
        name="Mock-GPU-RTX-3060 (dev)",
        vram_mb=12288,
        cuda_version="12.2",
        driver_version="535.0.0-mock",
    ).to_dict()
