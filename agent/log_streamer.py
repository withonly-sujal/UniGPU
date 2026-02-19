"""
UniGPU Agent — Log Streamer
Attaches to a running Docker container and streams log lines
to the backend via WebSocket in batches.
"""

import asyncio
import logging
import time
from typing import Any, Optional

logger = logging.getLogger("unigpu.agent.log_streamer")


class LogStreamer:
    """
    Streams container logs to the backend in near-real-time batches.

    Usage:
        streamer = LogStreamer(ws_client, batch_interval=0.2)
        await streamer.stream(job_id, container)
    """

    def __init__(self, ws_client: Any, batch_interval: float = 0.2):
        """
        Args:
            ws_client: AgentWebSocket instance with send_log() method.
            batch_interval: Seconds between sending batched log lines.
        """
        self.ws_client = ws_client
        self.batch_interval = batch_interval

    async def stream(self, job_id: str, container: Any) -> None:
        """
        Stream logs from a Docker container until it exits.

        Args:
            job_id: The job identifier for log association.
            container: A docker.models.containers.Container instance.
        """
        logger.info("Starting log stream for job %s", job_id)
        buffer: list[str] = []
        last_flush = time.time()

        try:
            # Get a streaming log generator (blocking I/O — run in thread)
            log_gen = container.logs(stream=True, follow=True, timestamps=True)

            loop = asyncio.get_event_loop()

            while True:
                # Read next log chunk in a thread to avoid blocking the event loop
                try:
                    chunk: Optional[bytes] = await asyncio.wait_for(
                        loop.run_in_executor(None, self._next_chunk, log_gen),
                        timeout=5.0,
                    )
                except asyncio.TimeoutError:
                    # No output for 5s — flush buffer and check if container is still running
                    await self._flush(job_id, buffer)
                    buffer.clear()
                    if not self._is_running(container):
                        break
                    continue

                if chunk is None:
                    # Stream exhausted — container exited
                    break

                line = chunk.decode("utf-8", errors="replace").rstrip("\n")
                if line:
                    buffer.append(line)

                # Flush if batch interval has elapsed
                now = time.time()
                if now - last_flush >= self.batch_interval and buffer:
                    await self._flush(job_id, buffer)
                    buffer.clear()
                    last_flush = now

        except Exception as exc:
            logger.error("Log streaming error for job %s: %s", job_id, exc)
            buffer.append(f"[AGENT ERROR] Log streaming interrupted: {exc}")

        finally:
            # Final flush
            if buffer:
                await self._flush(job_id, buffer)
            logger.info("Log stream ended for job %s", job_id)

    async def _flush(self, job_id: str, lines: list[str]) -> None:
        """Send buffered lines to backend."""
        if not lines:
            return
        try:
            await self.ws_client.send_log(job_id, list(lines))
            logger.debug("Flushed %d log lines for job %s", len(lines), job_id)
        except Exception as exc:
            logger.warning("Failed to send logs for job %s: %s", job_id, exc)

    @staticmethod
    def _next_chunk(log_gen) -> Optional[bytes]:
        """Read next chunk from Docker log generator (blocking)."""
        try:
            return next(log_gen)
        except StopIteration:
            return None

    @staticmethod
    def _is_running(container) -> bool:
        """Check if the container is still running."""
        try:
            container.reload()
            return container.status == "running"
        except Exception:
            return False
