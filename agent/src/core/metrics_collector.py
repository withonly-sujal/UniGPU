"""
UniGPU Agent — System Metrics Collector
Collects GPU temperature, GPU utilisation, CPU usage, and RAM usage.
Uses nvidia-smi for GPU metrics and psutil for CPU/RAM.
"""

import logging
import subprocess
import shutil
import sys
from typing import Dict, Any, Optional

# On Windows, prevent subprocess from flashing a console window
_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

logger = logging.getLogger("unigpu.agent.metrics")

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning("psutil not installed — CPU/RAM metrics unavailable")


def collect_metrics() -> Dict[str, Any]:
    """
    Collect current system metrics.

    Returns a dict like:
        {
            "gpu_temp_c": 62,
            "gpu_util_pct": 85,
            "gpu_mem_used_mb": 4096,
            "gpu_mem_total_mb": 8192,
            "cpu_pct": 45.2,
            "mem_pct": 72.1
        }

    Missing values are set to None.
    """
    metrics: Dict[str, Any] = {
        "gpu_temp_c": None,
        "gpu_util_pct": None,
        "gpu_mem_used_mb": None,
        "gpu_mem_total_mb": None,
        "cpu_pct": None,
        "mem_pct": None,
    }

    # ── GPU metrics via nvidia-smi ──
    _collect_gpu_metrics(metrics)

    # ── CPU & RAM via psutil ──
    _collect_cpu_ram_metrics(metrics)

    return metrics


def _collect_gpu_metrics(metrics: Dict[str, Any]) -> None:
    """Query nvidia-smi for GPU temp, utilisation, and memory."""
    if not shutil.which("nvidia-smi"):
        return

    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=_SUBPROCESS_FLAGS,
        )
        if result.returncode != 0:
            return

        # Take the first GPU line
        line = result.stdout.strip().splitlines()[0]
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 4:
            metrics["gpu_temp_c"] = int(parts[0])
            metrics["gpu_util_pct"] = int(parts[1])
            metrics["gpu_mem_used_mb"] = int(parts[2])
            metrics["gpu_mem_total_mb"] = int(parts[3])

    except Exception as exc:
        logger.debug("GPU metrics collection failed: %s", exc)


def _collect_cpu_ram_metrics(metrics: Dict[str, Any]) -> None:
    """Query psutil for CPU and RAM usage."""
    if not HAS_PSUTIL:
        return

    try:
        metrics["cpu_pct"] = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        metrics["mem_pct"] = round(mem.percent, 1)
    except Exception as exc:
        logger.debug("CPU/RAM metrics collection failed: %s", exc)
