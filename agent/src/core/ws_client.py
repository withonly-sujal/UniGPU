"""
UniGPU Agent — WebSocket Client
Persistent async WebSocket connection to the UniGPU backend.
Handles heartbeats, job dispatch, log streaming, and auto-reconnect.

Protocol (aligned with backend/app/routers/ws.py):
  Agent → Server:
    {"type": "heartbeat"}
    {"type": "job_status", "job_id": "...", "status": "running|completed|failed"}
    {"type": "log", "job_id": "...", "data": "..."}

  Server → Agent:
    {"type": "assign_job", "job_id": "...", "script_url": "/jobs/.../download/...", "requirements_url": "..."|null}
"""

import asyncio
import json
import logging
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional

import websockets
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedError,
    InvalidStatusCode,
)

logger = logging.getLogger("unigpu.agent.ws_client")

# Type alias for message handler callbacks
MessageHandler = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]


class AgentWebSocket:
    """
    Manages the persistent WebSocket connection between the GPU agent and the backend.

    Features:
      - Connect at /ws/agent/{gpu_id} (backend identifies agent by URL)
      - Periodic heartbeat
      - Dispatch incoming messages to registered handlers
      - Auto-reconnect with exponential backoff
      - Send log data, status updates, and job results
    """

    def __init__(
        self,
        ws_url: str,
        heartbeat_interval: int = 10,
    ):
        """
        Args:
            ws_url: Full WebSocket URL including gpu_id, e.g. ws://host/ws/agent/{gpu_id}
            heartbeat_interval: Seconds between heartbeats.
        """
        self.ws_url = ws_url
        self.heartbeat_interval = heartbeat_interval

        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._handlers: Dict[str, MessageHandler] = {}
        self._connected = asyncio.Event()
        self._should_run = True
        self._reconnect_delay = 1  # seconds, grows with backoff

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    def on(self, message_type: str, handler: MessageHandler) -> None:
        """Register a handler for a specific incoming message type."""
        self._handlers[message_type] = handler

    async def start(self) -> None:
        """Start the connection loop (blocks until stop() is called)."""
        while self._should_run:
            try:
                await self._connect_and_listen()
            except (ConnectionClosed, ConnectionClosedError, OSError) as exc:
                logger.warning("WebSocket disconnected: %s", exc)
            except InvalidStatusCode as exc:
                logger.error("WebSocket rejected (HTTP %s) — check GPU_ID/token", exc.status_code)
            except Exception as exc:
                logger.error("Unexpected WS error: %s", exc, exc_info=True)

            if self._should_run:
                logger.info("Reconnecting in %ss…", self._reconnect_delay)
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, 60)

    async def stop(self) -> None:
        """Gracefully shut down the WebSocket connection."""
        self._should_run = False
        if self._ws:
            await self._ws.close()
        self._connected.clear()

    async def send(self, message: Dict[str, Any]) -> None:
        """Send a JSON message to the backend. Waits until connected."""
        await self._connected.wait()
        if self._ws:
            await self._ws.send(json.dumps(message))

    async def send_log(self, job_id: str, data: str) -> None:
        """
        Send log data for a running job.
        Backend expects: {"type": "log", "job_id": "...", "data": "..."}
        """
        await self.send({
            "type": "log",
            "job_id": job_id,
            "data": data,
        })

    async def send_job_status(self, job_id: str, status: str, retries: int = 3) -> None:
        """
        Report job status change with retry logic.
        Backend expects: {"type": "job_status", "job_id": "...", "status": "running|completed|failed"}
        Retries on disconnect so status is never lost.
        """
        msg = {
            "type": "job_status",
            "job_id": job_id,
            "status": status,
        }
        for attempt in range(1, retries + 1):
            try:
                await self.send(msg)
                logger.info("Sent job_status=%s for %s (attempt %d)", status, job_id, attempt)
                return
            except Exception as exc:
                logger.warning(
                    "Failed to send job_status=%s for %s (attempt %d/%d): %s",
                    status, job_id, attempt, retries, exc,
                )
                if attempt < retries:
                    # Wait for reconnection before retrying
                    self._connected.clear()
                    await asyncio.sleep(2)
                    await self._connected.wait()
                else:
                    logger.error("Gave up sending job_status=%s for %s after %d attempts", status, job_id, retries)

    async def send_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Send system metrics (GPU temp, GPU util, CPU, RAM) to backend.
        Backend expects: {"type": "metrics", "data": {...}}
        """
        await self.send({
            "type": "metrics",
            "data": metrics,
        })

    async def send_agent_log(self, data: str) -> None:
        """
        Send agent log lines to backend for relay to provider dashboard.
        Backend expects: {"type": "agent_log", "data": "..."}
        """
        await self.send({
            "type": "agent_log",
            "data": data,
        })

    # ──────────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────────

    async def _connect_and_listen(self) -> None:
        """Establish connection, then run heartbeat + listener concurrently."""
        async with websockets.connect(
            self.ws_url,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
        ) as ws:
            self._ws = ws
            self._connected.set()
            self._reconnect_delay = 1  # reset on successful connect
            logger.info("Connected to backend at %s", self.ws_url)

            # Run heartbeat and listener concurrently
            heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            listener_task = asyncio.create_task(self._listen_loop())

            try:
                done, pending = await asyncio.wait(
                    [heartbeat_task, listener_task],
                    return_when=asyncio.FIRST_EXCEPTION,
                )
                for task in done:
                    task.result()  # re-raise any exception
            finally:
                heartbeat_task.cancel()
                listener_task.cancel()
                self._connected.clear()

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat messages."""
        while self._should_run:
            try:
                await self._ws.send(json.dumps({
                    "type": "heartbeat",
                }))
                logger.debug("♥ heartbeat sent")
            except ConnectionClosed:
                break
            await asyncio.sleep(self.heartbeat_interval)

    async def _listen_loop(self) -> None:
        """Listen for incoming messages and dispatch to handlers."""
        async for raw in self._ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Received non-JSON message: %s", raw[:200])
                continue

            msg_type = msg.get("type", "unknown")
            logger.debug("Received message type=%s", msg_type)

            handler = self._handlers.get(msg_type)
            if handler:
                try:
                    await handler(msg)
                except Exception as exc:
                    logger.error("Handler for '%s' raised: %s", msg_type, exc, exc_info=True)
            else:
                logger.warning("No handler registered for message type '%s'", msg_type)
