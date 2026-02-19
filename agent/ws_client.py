"""
UniGPU Agent — WebSocket Client
Persistent async WebSocket connection to the UniGPU backend.
Handles registration, heartbeats, job dispatch, log streaming, and auto-reconnect.
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
      - Register with GPU specs on connect
      - Periodic heartbeat
      - Dispatch incoming messages to registered handlers
      - Auto-reconnect with exponential backoff
      - Send log lines, status updates, and job results
    """

    def __init__(
        self,
        ws_url: str,
        agent_token: str,
        gpu_specs: List[Dict[str, Any]],
        heartbeat_interval: int = 10,
    ):
        self.ws_url = ws_url
        self.agent_token = agent_token
        self.gpu_specs = gpu_specs
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
                logger.error("WebSocket rejected (HTTP %s) — check token/URL", exc.status_code)
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

    async def send_log(self, job_id: str, lines: List[str]) -> None:
        """Send a batch of log lines for a running job."""
        await self.send({
            "type": "log_lines",
            "job_id": job_id,
            "lines": lines,
            "timestamp": time.time(),
        })

    async def send_job_result(self, job_id: str, status: str, runtime_seconds: float, exit_code: int, error: Optional[str] = None) -> None:
        """Report job completion or failure."""
        await self.send({
            "type": "job_result",
            "job_id": job_id,
            "status": status,
            "runtime_seconds": runtime_seconds,
            "exit_code": exit_code,
            "error": error,
            "timestamp": time.time(),
        })

    async def send_status_update(self, status: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Send an agent status update (e.g. 'idle', 'busy', 'error')."""
        await self.send({
            "type": "agent_status",
            "status": status,
            "metadata": metadata or {},
            "timestamp": time.time(),
        })

    # ──────────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────────

    async def _connect_and_listen(self) -> None:
        """Establish connection, register, then run heartbeat + listener concurrently."""
        extra_headers = {"Authorization": f"Bearer {self.agent_token}"}
        async with websockets.connect(
            self.ws_url,
            extra_headers=extra_headers,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
        ) as ws:
            self._ws = ws
            self._connected.set()
            self._reconnect_delay = 1  # reset on successful connect
            logger.info("Connected to backend at %s", self.ws_url)

            # Register
            await self._register()

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

    async def _register(self) -> None:
        """Send registration payload with GPU specs."""
        payload = {
            "type": "register",
            "agent_token": self.agent_token,
            "gpus": self.gpu_specs,
            "timestamp": time.time(),
        }
        await self._ws.send(json.dumps(payload))
        logger.info("Registered with backend (%d GPU(s))", len(self.gpu_specs))

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat messages."""
        while self._should_run:
            try:
                await self._ws.send(json.dumps({
                    "type": "heartbeat",
                    "timestamp": time.time(),
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

            if msg_type == "pong":
                continue  # heartbeat ack, no action needed

            handler = self._handlers.get(msg_type)
            if handler:
                try:
                    await handler(msg)
                except Exception as exc:
                    logger.error("Handler for '%s' raised: %s", msg_type, exc, exc_info=True)
            else:
                logger.warning("No handler registered for message type '%s'", msg_type)
