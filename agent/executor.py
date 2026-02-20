"""
UniGPU Agent — Docker Job Executor
Reads training scripts from local paths (as stored by the backend),
builds/runs containers with NVIDIA runtime,
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
      1. Copy training script from backend's upload dir into job work directory
      2. Create and start a container with resource limits
      3. Monitor for completion or timeout
      4. Collect exit code and output
    """

    def __init__(
        self,
        work_dir: str,
        docker_base_image: str,
        backend_http_url: str = "http://localhost:8000",
        cpu_limit: float = 4.0,
        memory_limit: str = "8g",
        max_timeout: int = 3600,
    ):
        self.work_dir = Path(work_dir)
        self.docker_base_image = docker_base_image
        self.backend_http_url = backend_http_url.rstrip("/")
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

        Expected job payload (from backend assign_job):
          {
            "type": "assign_job",
            "job_id": "uuid",
            "script_url": "/jobs/<job_id>/download/train.py",
            "requirements_url": "/jobs/<job_id>/download/requirements.txt" | null,
          }
        """
        job_id = job["job_id"]
        logger.info("Starting job %s", job_id)

        try:
            # Step 1: Prepare directories
            job_dir = self._prepare_job_dir(job_id)
            input_dir = job_dir / "input"
            output_dir = job_dir / "output"
            input_dir.mkdir(exist_ok=True)
            output_dir.mkdir(exist_ok=True)

            # Step 2: Download files from backend via HTTP
            await self._download_files(job, input_dir)

            # Step 3: Run Docker container (blocking, run in executor)
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

    async def _download_files(self, job: Dict[str, Any], dest: Path) -> None:
        """
        Download job files (script + optional requirements) from the backend
        via HTTP. The backend serves them at /jobs/{id}/download/{filename}.
        """
        async with httpx.AsyncClient(base_url=self.backend_http_url, timeout=60) as client:
            # Download script (required)
            script_url = job["script_url"]
            script_name = Path(script_url).name
            resp = await client.get(script_url)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Failed to download script from {script_url}: HTTP {resp.status_code}"
                )
            (dest / script_name).write_bytes(resp.content)
            logger.info("Downloaded script %s (%d bytes)", script_name, len(resp.content))

            # Download requirements (optional)
            req_url = job.get("requirements_url")
            if req_url:
                req_name = Path(req_url).name
                resp = await client.get(req_url)
                if resp.status_code == 200:
                    (dest / req_name).write_bytes(resp.content)
                    logger.info("Downloaded requirements %s (%d bytes)", req_name, len(resp.content))
                else:
                    logger.warning("Requirements download returned HTTP %d — skipping", resp.status_code)

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
        image = self.docker_base_image
        timeout = self.max_timeout

        # Determine script name from the URL
        script_name = Path(job["script_url"]).name

        client = self._get_docker_client()

        # Ensure image is available
        self._ensure_image(client, image)

        # Build command: install deps then run script
        cmd_parts = []
        req_url = job.get("requirements_url")
        if req_url:
            req_name = Path(req_url).name
            if (input_dir / req_name).exists():
                cmd_parts.append(f"pip install -q -r /workspace/input/{req_name} &&")
        cmd_parts.append(f"python /workspace/input/{script_name}")
        full_cmd = " ".join(cmd_parts)

        start_time = time.time()
        container = None

        try:
            # Detect if NVIDIA runtime is available
            runtime_opts = {}
            try:
                runtimes = client.info().get("Runtimes", {})
                if "nvidia" in runtimes:
                    runtime_opts["runtime"] = "nvidia"
                    runtime_opts["environment"] = {"NVIDIA_VISIBLE_DEVICES": "all"}
                    logger.info("Using NVIDIA runtime for job %s", job_id)
                else:
                    logger.warning("NVIDIA runtime not found — running without GPU access")
            except Exception:
                logger.warning("Could not detect runtimes — running without GPU access")

            container = client.containers.run(
                image=image,
                command=["bash", "-c", full_cmd],
                name=f"unigpu-job-{job_id}",
                detach=True,
                **runtime_opts,
                volumes={
                    str(input_dir.resolve()): {"bind": "/workspace/input", "mode": "ro"},
                    str(output_dir.resolve()): {"bind": "/workspace/output", "mode": "rw"},
                },
                working_dir="/workspace",
                cpu_period=100000,
                cpu_quota=int(self.cpu_limit * 100000),
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
