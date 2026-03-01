from fastapi import WebSocket
from typing import Dict, Set


class ConnectionManager:
    """Manages active WebSocket connections from GPU agents AND provider dashboards."""

    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}  # gpu_id → WebSocket
        self._provider_connections: Dict[str, Set[WebSocket]] = {}  # provider_id → set of WebSockets
        self._gpu_to_provider: Dict[str, str] = {}  # gpu_id → provider_id (cache)

    # ── Agent connections ──

    async def connect(self, gpu_id: str, websocket: WebSocket):
        await websocket.accept()
        self._connections[gpu_id] = websocket

    def disconnect(self, gpu_id: str):
        self._connections.pop(gpu_id, None)
        self._gpu_to_provider.pop(gpu_id, None)

    def is_connected(self, gpu_id: str) -> bool:
        return gpu_id in self._connections

    async def send_to_gpu(self, gpu_id: str, message: dict):
        ws = self._connections.get(gpu_id)
        if ws:
            await ws.send_json(message)

    def get_active_gpu_ids(self) -> list[str]:
        return list(self._connections.keys())

    # ── Provider dashboard connections ──

    async def connect_provider(self, provider_id: str, websocket: WebSocket):
        await websocket.accept()
        if provider_id not in self._provider_connections:
            self._provider_connections[provider_id] = set()
        self._provider_connections[provider_id].add(websocket)

    def disconnect_provider(self, provider_id: str, websocket: WebSocket):
        conns = self._provider_connections.get(provider_id)
        if conns:
            conns.discard(websocket)
            if not conns:
                del self._provider_connections[provider_id]

    async def send_to_provider(self, provider_id: str, message: dict):
        """Send a message to all connected provider dashboard WebSockets."""
        conns = self._provider_connections.get(provider_id, set())
        dead = []
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            conns.discard(ws)

    # ── GPU ↔ Provider mapping ──

    def set_gpu_provider(self, gpu_id: str, provider_id: str):
        """Cache the mapping from gpu_id to provider_id."""
        self._gpu_to_provider[gpu_id] = provider_id

    def get_provider_for_gpu(self, gpu_id: str) -> str | None:
        """Get the provider_id that owns this gpu_id."""
        return self._gpu_to_provider.get(gpu_id)


# Singleton instance shared across the app
manager = ConnectionManager()
