"""
UniGPU Agent — Configuration
Loads settings from environment variables / .env file.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from agent directory
load_dotenv(Path(__file__).parent / ".env")


@dataclass(frozen=True)
class AgentConfig:
    """Immutable agent configuration loaded from environment."""

    # Backend endpoints
    backend_ws_url: str = field(
        default_factory=lambda: os.getenv("BACKEND_WS_URL", "ws://localhost:8000/ws/agent")
    )
    backend_http_url: str = field(
        default_factory=lambda: os.getenv("BACKEND_HTTP_URL", "http://localhost:8000")
    )

    # Authentication
    agent_token: str = field(
        default_factory=lambda: os.getenv("AGENT_TOKEN", "dev-agent-token")
    )

    # Heartbeat
    heartbeat_interval: int = field(
        default_factory=lambda: int(os.getenv("HEARTBEAT_INTERVAL", "10"))
    )

    # Work directory for job files & outputs
    work_dir: str = field(
        default_factory=lambda: os.getenv("WORK_DIR", "./workdir")
    )

    # Maximum job execution time in seconds
    max_job_timeout: int = field(
        default_factory=lambda: int(os.getenv("MAX_JOB_TIMEOUT", "3600"))
    )

    # Docker base image for jobs
    docker_base_image: str = field(
        default_factory=lambda: os.getenv("DOCKER_BASE_IMAGE", "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime")
    )

    # Resource limits
    cpu_limit: float = field(
        default_factory=lambda: float(os.getenv("CPU_LIMIT", "4.0"))
    )
    memory_limit: str = field(
        default_factory=lambda: os.getenv("MEMORY_LIMIT", "8g")
    )

    # Log batching interval (seconds)
    log_batch_interval: float = field(
        default_factory=lambda: float(os.getenv("LOG_BATCH_INTERVAL", "0.2"))
    )

    def ensure_work_dir(self) -> Path:
        """Create and return the work directory path."""
        path = Path(self.work_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def __str__(self) -> str:
        return (
            f"AgentConfig(\n"
            f"  backend_ws_url={self.backend_ws_url}\n"
            f"  backend_http_url={self.backend_http_url}\n"
            f"  heartbeat_interval={self.heartbeat_interval}s\n"
            f"  work_dir={self.work_dir}\n"
            f"  max_job_timeout={self.max_job_timeout}s\n"
            f"  docker_base_image={self.docker_base_image}\n"
            f"  cpu_limit={self.cpu_limit} | memory_limit={self.memory_limit}\n"
            f")"
        )
