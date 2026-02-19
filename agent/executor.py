"""
UniGPU Agent — Docker Job Executor
Downloads training scripts, builds/runs containers with NVIDIA runtime,
enforces resource limits & timeouts, and collects results.
"""

import asyncio
import logging
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import docker
import httpx
from docker.errors import (
    ContainerError,
    DockerException,
    ImageNotFound,
    NotFound,
)

logger = logging.getLogger("unigpu.agent.executor")


@dataclass
class JobResult:
    """Result of a single job execution."""
    job_id: str
    status: str          # "completed" | "failed" | "timeout" | "error"
    exit_code: int
    runtime_seconds: float
    output_dir: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "exit_code": self.exit_code,
            "runtime_seconds": round(self.runtime_seconds, 2),
            "output_dir": self.output_dir,
            "error_message": self.error_message,
        }


class JobExecutor:
    """
    Executes training jobs inside Docker containers using NVIDIA runtime.

    Lifecycle:
      1. Download training script from backend
      2. Prepare job work directory
      3. Create and start a container with resource limits
      4. Monitor for completion or timeout
      5. Collect exit code and output
    """

    def __init__(
        self,
        backend_http_url: str,
        agent_token: str,
        work_dir: str,
        docker_base_image: str,
        cpu_limit: float = 4.0,
        memory_limit: str = "8g",
        max_timeout: int = 3600,
    ):
        self.backend_http_url = backend_http_url.rstrip("/")
        self.agent_token = agent_token
        self.work_dir = Path(work_dir)
        self.docker_base_image = docker_base_image
        self.cpu_limit = cpu_limit
        self.memory_limit = memory_limit
        self.max_timeout = max_timeout

        self._docker: Optional[docker.DockerClient] = None

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    async def execute(self, job: Dict[str, Any]) -> JobResult:
        """
        Run a job end-to-end.

        Expected job payload:
          {
            "job_id": "uuid",
            "script_url": "/api/jobs/<id>/script",
            "script_name": "train.py",
            "requirements": "torch\\nnumpy\\n...",   # optional
            "args": ["--epochs", "10"],               # optional
            "timeout": 1800,                          # optional override
            "image": "pytorch/pytorch:latest",        # optional override
          }
        """
        job_id = job["job_id"]
        logger.info("▶ Starting job %s", job_id)

        try:
            # Step 1: Prepare directories
            job_dir = self._prepare_job_dir(job_id)
            input_dir = job_dir / "input"
            output_dir = job_dir / "output"
            input_dir.mkdir(exist_ok=True)
            output_dir.mkdir(exist_ok=True)

            # Step 2: Download training script
            await self._download_script(job, input_dir)

            # Step 3: Write requirements if provided
            if job.get("requirements"):
                (input_dir / "requirements.txt").write_text(job["requirements"])

            # Step 4: Run Docker container (blocking, run in executor)
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self._run_container,
                job, input_dir, output_dir,
            )
            return result

        except Exception as exc:
            logger.exception("Job %s failed with unexpected error", job_id)
            return JobResult(
                job_id=job_id,
                status="error",
                exit_code=-1,
                runtime_seconds=0,
                error_message=str(exc),
            )

    def get_container_for_job(self, job_id: str) -> Optional[Any]:
        """Get the running Docker container for a job (for log streaming)."""
        client = self._get_docker_client()
        try:
            return client.containers.get(f"unigpu-job-{job_id}")
        except NotFound:
            return None

    # ──────────────────────────────────────────────
    # Internal — File operations
    # ──────────────────────────────────────────────

    def _prepare_job_dir(self, job_id: str) -> Path:
        """Create a clean working directory for this job."""
        job_dir = self.work_dir / job_id
        if job_dir.exists():
            shutil.rmtree(job_dir)
        job_dir.mkdir(parents=True)
        return job_dir

    async def _download_script(self, job: Dict[str, Any], dest: Path) -> None:
        """Download the training script from the backend."""
        script_url = f"{self.backend_http_url}{job['script_url']}"
        script_name = job.get("script_name", "train.py")

        async with httpx.AsyncClient(timeout=60) as client:
            headers = {"Authorization": f"Bearer {self.agent_token}"}
            resp = await client.get(script_url, headers=headers)
            resp.raise_for_status()
            (dest / script_name).write_bytes(resp.content)

        logger.info("Downloaded %s (%d bytes)", script_name, len(resp.content))

    # ──────────────────────────────────────────────
    # Internal — Docker execution
    # ──────────────────────────────────────────────

    def _get_docker_client(self) -> docker.DockerClient:
        """Lazy-init Docker client."""
        if self._docker is None:
            self._docker = docker.from_env()
        return self._docker

    def _run_container(
        self,
        job: Dict[str, Any],
        input_dir: Path,
        output_dir: Path,
    ) -> JobResult:
        """
        Create and run a Docker container for the job.
        This is a BLOCKING call — should be run via run_in_executor.
        """
        job_id = job["job_id"]
        image = job.get("image", self.docker_base_image)
        script_name = job.get("script_name", "train.py")
        args = job.get("args", [])
        timeout = min(job.get("timeout", self.max_timeout), self.max_timeout)

        client = self._get_docker_client()

        # Ensure image is available
        self._ensure_image(client, image)

        # Build command: install deps then run script
        cmd_parts = []
        if (input_dir / "requirements.txt").exists():
            cmd_parts.append("pip install -q -r /workspace/input/requirements.txt &&")
        cmd_parts.append(f"python /workspace/input/{script_name}")
        if args:
            cmd_parts.append(" ".join(args))
        full_cmd = " ".join(cmd_parts)

        start_time = time.time()
        container = None

        try:
            container = client.containers.run(
                image=image,
                command=["bash", "-c", full_cmd],
                name=f"unigpu-job-{job_id}",
                detach=True,
                runtime="nvidia",                         # NVIDIA GPU runtime
                environment={"NVIDIA_VISIBLE_DEVICES": "all"},
                volumes={
                    str(input_dir.resolve()): {"bind": "/workspace/input", "mode": "ro"},
                    str(output_dir.resolve()): {"bind": "/workspace/output", "mode": "rw"},
                },
                working_dir="/workspace",
                cpu_period=100000,
                cpu_quota=int(self.cpu_limit * 100000),    # e.g. 4 cores
                mem_limit=self.memory_limit,
                network_mode="bridge",
                auto_remove=False,
            )

            logger.info("Container %s started for job %s", container.short_id, job_id)

            # Wait for container to finish or timeout
            result = container.wait(timeout=timeout)
            elapsed = time.time() - start_time
            exit_code = result.get("StatusCode", -1)

            status = "completed" if exit_code == 0 else "failed"
            logger.info(
                "Job %s %s (exit=%d, %.1fs)",
                job_id, status, exit_code, elapsed,
            )

            return JobResult(
                job_id=job_id,
                status=status,
                exit_code=exit_code,
                runtime_seconds=elapsed,
                output_dir=str(output_dir),
            )

        except Exception as exc:
            elapsed = time.time() - start_time

            if "timed out" in str(exc).lower() or "read timed out" in str(exc).lower():
                logger.warning("Job %s timed out after %.1fs", job_id, elapsed)
                return JobResult(
                    job_id=job_id,
                    status="timeout",
                    exit_code=-1,
                    runtime_seconds=elapsed,
                    error_message=f"Exceeded {timeout}s timeout",
                )

            logger.exception("Container execution error for job %s", job_id)
            return JobResult(
                job_id=job_id,
                status="error",
                exit_code=-1,
                runtime_seconds=elapsed,
                error_message=str(exc),
            )

        finally:
            # Cleanup container
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

    def _ensure_image(self, client: docker.DockerClient, image: str) -> None:
        """Pull image if not available locally."""
        try:
            client.images.get(image)
            logger.debug("Image %s already available", image)
        except ImageNotFound:
            logger.info("Pulling image %s (this may take a while)…", image)
            client.images.pull(image)
            logger.info("Image %s pulled successfully", image)
