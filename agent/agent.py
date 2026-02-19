"""
UniGPU GPU Agent — Main Entry Point
===================================
A lightweight compute agent that runs on provider (student) machines.

Responsibilities:
  • Detect GPU hardware (name, VRAM, CUDA version)
  • Connect to the UniGPU backend via WebSocket
  • Send periodic heartbeats
  • Receive job assignments
  • Execute jobs inside Docker containers with NVIDIA runtime
  • Stream logs in real time
  • Upload output artifacts
  • Report job completion / failure
  • Handle reconnects and fault recovery

Usage:
    python agent.py
"""

import asyncio
import logging
import os
import signal
import sys
from typing import Any, Dict

# ── Agent modules ─────────────────────────────────
from config import AgentConfig
from gpu_detector import detect_gpus
from ws_client import AgentWebSocket
from executor import JobExecutor
from log_streamer import LogStreamer
from uploader import ArtifactUploader

# ── Logging ───────────────────────────────────────
LOG_FORMAT = "%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("unigpu.agent")


class UniGPUAgent:
    """
    Main orchestrator for the GPU agent.
    Ties together GPU detection, WebSocket communication, job execution,
    log streaming, and artifact uploading.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.gpu_specs = []
        self.ws: AgentWebSocket | None = None
        self.executor: JobExecutor | None = None
        self.log_streamer: LogStreamer | None = None
        self.uploader: ArtifactUploader | None = None
        self._current_job_id: str | None = None
        self._shutdown_event = asyncio.Event()

    # ──────────────────────────────────────────────
    # Bootstrap
    # ──────────────────────────────────────────────

    async def start(self) -> None:
        """Boot the agent and enter the main event loop."""
        self._print_banner()
        logger.info("Configuration:\n%s", self.config)

        # 1. Ensure work directory
        work_dir = self.config.ensure_work_dir()
        logger.info("Work directory: %s", work_dir.resolve())

        # 2. Detect GPUs
        self.gpu_specs = detect_gpus()
        logger.info("GPU(s) detected: %s", [g["name"] for g in self.gpu_specs])

        # 3. Initialise components
        self.executor = JobExecutor(
            backend_http_url=self.config.backend_http_url,
            agent_token=self.config.agent_token,
            work_dir=self.config.work_dir,
            docker_base_image=self.config.docker_base_image,
            cpu_limit=self.config.cpu_limit,
            memory_limit=self.config.memory_limit,
            max_timeout=self.config.max_job_timeout,
        )

        self.ws = AgentWebSocket(
            ws_url=self.config.backend_ws_url,
            agent_token=self.config.agent_token,
            gpu_specs=self.gpu_specs,
            heartbeat_interval=self.config.heartbeat_interval,
        )

        self.log_streamer = LogStreamer(
            ws_client=self.ws,
            batch_interval=self.config.log_batch_interval,
        )

        self.uploader = ArtifactUploader(
            backend_http_url=self.config.backend_http_url,
            agent_token=self.config.agent_token,
        )

        # 4. Register message handlers
        self.ws.on("job_assign", self._handle_job_assign)
        self.ws.on("cancel_job", self._handle_cancel_job)
        self.ws.on("ping", self._handle_ping)

        # 5. Setup signal handlers for graceful shutdown
        self._setup_signals()

        # 6. Run WebSocket (blocks until shutdown)
        logger.info("🚀 Agent is starting — connecting to %s", self.config.backend_ws_url)
        try:
            await self.ws.start()
        except asyncio.CancelledError:
            pass
        finally:
            logger.info("Agent shut down cleanly.")

    async def stop(self) -> None:
        """Graceful shutdown."""
        logger.info("Shutting down agent…")
        self._shutdown_event.set()
        if self.ws:
            await self.ws.send_status_update("offline")
            await self.ws.stop()

    # ──────────────────────────────────────────────
    # Message Handlers
    # ──────────────────────────────────────────────

    async def _handle_job_assign(self, msg: Dict[str, Any]) -> None:
        """Handle an incoming job assignment from the backend."""
        job = msg.get("job", msg)  # support both wrapped and flat payloads
        job_id = job.get("job_id", "unknown")

        if self._current_job_id:
            logger.warning(
                "Received job %s but already running %s — rejecting",
                job_id, self._current_job_id,
            )
            await self.ws.send_job_result(
                job_id=job_id,
                status="rejected",
                runtime_seconds=0,
                exit_code=-1,
                error="Agent is busy with another job",
            )
            return

        self._current_job_id = job_id
        await self.ws.send_status_update("busy", {"job_id": job_id})
        logger.info("═══════════════════════════════════════")
        logger.info("  JOB RECEIVED: %s", job_id)
        logger.info("═══════════════════════════════════════")

        try:
            # Start execution
            result = await self._execute_with_streaming(job)

            # Upload artifacts if job produced output
            if result.output_dir:
                upload_ok = await self.uploader.upload(job_id, result.output_dir)
                if not upload_ok:
                    logger.warning("Artifact upload failed for job %s", job_id)

            # Report result to backend
            await self.ws.send_job_result(
                job_id=result.job_id,
                status=result.status,
                runtime_seconds=result.runtime_seconds,
                exit_code=result.exit_code,
                error=result.error_message,
            )

            logger.info(
                "Job %s finished — status=%s, exit=%d, time=%.1fs",
                job_id, result.status, result.exit_code, result.runtime_seconds,
            )

        except Exception as exc:
            logger.exception("Unhandled error running job %s", job_id)
            await self.ws.send_job_result(
                job_id=job_id,
                status="error",
                runtime_seconds=0,
                exit_code=-1,
                error=str(exc),
            )

        finally:
            self._current_job_id = None
            await self.ws.send_status_update("idle")

    async def _execute_with_streaming(self, job: Dict[str, Any]):
        """Run the job and concurrently stream its logs."""
        job_id = job.get("job_id", "unknown")

        # Start execution in background
        exec_task = asyncio.create_task(self.executor.execute(job))

        # Give the container a moment to start
        await asyncio.sleep(2)

        # Try to attach log streamer
        container = self.executor.get_container_for_job(job_id)
        if container:
            stream_task = asyncio.create_task(
                self.log_streamer.stream(job_id, container)
            )
            result = await exec_task
            stream_task.cancel()
            try:
                await stream_task
            except asyncio.CancelledError:
                pass
        else:
            logger.warning("Could not attach log streamer — container not found")
            result = await exec_task

        return result

    async def _handle_cancel_job(self, msg: Dict[str, Any]) -> None:
        """Handle a job cancellation request."""
        job_id = msg.get("job_id", "unknown")
        logger.info("Cancel requested for job %s", job_id)

        if self._current_job_id == job_id:
            container = self.executor.get_container_for_job(job_id)
            if container:
                try:
                    container.kill()
                    logger.info("Killed container for job %s", job_id)
                except Exception as exc:
                    logger.error("Failed to kill container: %s", exc)
        else:
            logger.warning("Cancel for job %s but not currently running it", job_id)

    async def _handle_ping(self, msg: Dict[str, Any]) -> None:
        """Respond to a ping from the backend."""
        await self.ws.send({"type": "pong", "timestamp": msg.get("timestamp")})

    # ──────────────────────────────────────────────
    # Utilities
    # ──────────────────────────────────────────────

    def _setup_signals(self) -> None:
        """Register OS signal handlers for graceful shutdown."""
        loop = asyncio.get_event_loop()

        def _signal_handler():
            logger.info("Received shutdown signal")
            asyncio.ensure_future(self.stop())

        if sys.platform != "win32":
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, _signal_handler)
        # On Windows, KeyboardInterrupt is caught in main()

    @staticmethod
    def _print_banner() -> None:
        banner = r"""
    ╔══════════════════════════════════════════════════╗
    ║                                                  ║
    ║         ██╗   ██╗███╗   ██╗██╗ ██████╗██████╗   ║
    ║         ██║   ██║████╗  ██║██║██╔════╝██╔══██╗  ║
    ║         ██║   ██║██╔██╗ ██║██║██║  ███████╗██║  ║
    ║         ██║   ██║██║╚██╗██║██║██║   ██╔═══██║   ║
    ║         ╚██████╔╝██║ ╚████║██║╚██████╗██████╔╝  ║
    ║          ╚═════╝ ╚═╝  ╚═══╝╚═╝ ╚═════╝╚═════╝  ║
    ║                                                  ║
    ║              GPU Agent  •  v0.1.0                ║
    ║         Peer-to-Peer GPU Marketplace             ║
    ║                                                  ║
    ╚══════════════════════════════════════════════════╝
        """
        print(banner)


# ──────────────────────────────────────────────────
# CLI Entry Point
# ──────────────────────────────────────────────────

def main():
    config = AgentConfig()
    agent = UniGPUAgent(config)

    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        logger.info("Interrupted — shutting down.")
        asyncio.run(agent.stop())


if __name__ == "__main__":
    main()
