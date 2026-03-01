"""
UniGPU Agent — System Tray Application
Provides a Windows system-tray icon with status indication, right-click menu,
and bridges to the agent's asyncio event loop running in a background thread.
"""

import asyncio
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("unigpu.agent.tray")

# Try to import pystray — fail gracefully for headless/CI
try:
    import pystray
    from pystray import MenuItem, Menu
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False
    logger.warning("pystray not installed — system tray unavailable")


# ─── Status colors ───────────────────────────────
STATUS_COLORS = {
    "connected":    "#22c55e",  # green
    "connecting":   "#facc15",  # yellow
    "disconnected": "#ef4444",  # red
    "idle":         "#6366f1",  # indigo (no job)
    "running_job":  "#22c55e",  # green (job active)
}

# ─── Icon generation ─────────────────────────────

def _create_icon_image(color: str = "#6366f1", size: int = 64) -> "Image.Image":
    """
    Generate a simple tray icon: a filled circle with 'U' letter on it.
    Color indicates status.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle
    padding = 4
    draw.ellipse(
        [padding, padding, size - padding, size - padding],
        fill=color,
    )

    # 'U' letter in center
    try:
        font = ImageFont.truetype("segoeui.ttf", size // 2)
    except (IOError, OSError):
        try:
            font = ImageFont.truetype("arial.ttf", size // 2)
        except (IOError, OSError):
            font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), "U", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (size - tw) // 2
    ty = (size - th) // 2 - 2
    draw.text((tx, ty), "U", fill="white", font=font)

    return img


class TrayApp:
    """
    System tray application for the UniGPU agent.

    Usage:
        tray = TrayApp(config, agent_class)
        tray.run()   # blocks — runs pystray in main thread
    """

    def __init__(self, config, agent_factory):
        """
        Args:
            config: AgentConfig instance
            agent_factory: callable that returns a UniGPUAgent given a config
        """
        if not HAS_TRAY:
            raise RuntimeError("pystray is not installed. Install it: pip install pystray")

        self.config = config
        self._agent_factory = agent_factory
        self._agent = None
        self._agent_thread: Optional[threading.Thread] = None
        self._agent_loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._status = "disconnected"
        self._current_job: Optional[str] = None
        self._icon: Optional[pystray.Icon] = None

        # Hidden root for tkinter dialogs (settings, etc.)
        self._tk_root = None
        self._exiting = False  # True when manually stopped from tray (prevents auto-restart polling)

    @property
    def status_text(self) -> str:
        if self._current_job:
            return f"Running job: {self._current_job[:8]}…"
        return self._status.replace("_", " ").title()

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    def run(self):
        """Start the tray icon and agent. Blocks until Exit is chosen."""
        self._icon = pystray.Icon(
            name="UniGPU Agent",
            icon=_create_icon_image(STATUS_COLORS.get(self._status, "#6366f1")),
            title=f"UniGPU Agent — {self.status_text}",
            menu=self._build_menu(),
        )

        # Start agent and make icon visible inside setup callback
        # (pystray on Windows requires this to be done AFTER run() starts)
        def _on_setup(icon):
            icon.visible = True
            self._start_agent()

            # Show a notification so the user knows the agent is running
            try:
                icon.notify(
                    "UniGPU Agent is running in the system tray.\n"
                    "Right-click the tray icon for options.",
                    title="UniGPU Agent Started",
                )
            except Exception:
                pass  # Some pystray backends don't support notify

        self._icon.run(setup=_on_setup)

    def update_status(self, status: str, job_id: Optional[str] = None):
        """Update the tray icon color and tooltip."""
        self._status = status
        self._current_job = job_id

        if self._icon:
            color = STATUS_COLORS.get(status, "#6366f1")
            self._icon.icon = _create_icon_image(color)
            self._icon.title = f"UniGPU Agent — {self.status_text}"
            self._icon.menu = self._build_menu()

    # ──────────────────────────────────────────────
    # Menu
    # ──────────────────────────────────────────────

    def _build_menu(self) -> "Menu":
        return Menu(
            MenuItem(lambda item: f"Status: {self.status_text}", None, enabled=False),
            Menu.SEPARATOR,
            MenuItem("Open Settings", self._on_open_settings),
            MenuItem("Open Log Folder", self._on_open_logs),
            Menu.SEPARATOR,
            MenuItem("Start Agent", self._on_start, visible=lambda item: not self._running),
            MenuItem("Stop Agent", self._on_stop, visible=lambda item: self._running),
            Menu.SEPARATOR,
            MenuItem("Exit", self._on_exit),
        )

    # ──────────────────────────────────────────────
    # Agent lifecycle (background thread)
    # ──────────────────────────────────────────────

    def _start_agent(self):
        if self._running:
            return

        self._running = True
        self.update_status("connecting")

        def _run_in_thread():
            self._agent_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._agent_loop)

            self._agent = self._agent_factory(self.config)

            # Monkey-patch the agent to update tray status
            original_handle = self._agent._handle_assign_job

            async def _patched_handle(msg):
                job_id = msg.get("job_id", "?")
                self.update_status("running_job", job_id)
                try:
                    await original_handle(msg)
                finally:
                    self.update_status("connected")

            self._agent._handle_assign_job = _patched_handle

            try:
                self.update_status("connected")
                self._agent_loop.run_until_complete(self._agent.start())
            except Exception as e:
                logger.error("Agent thread error: %s", e)
                self.update_status("disconnected")
            finally:
                self._running = False
                self.update_status("disconnected")

            # Agent stopped (e.g. from dashboard "Go Offline")
            # Poll backend until GPU status is set back to "online"
            self._poll_for_restart()

        self._agent_thread = threading.Thread(target=_run_in_thread, daemon=True)
        self._agent_thread.start()

    def _poll_for_restart(self):
        """Poll backend for GPU 'online' status and auto-restart the agent."""
        if self._exiting:
            return  # Don't poll if manually stopped from tray
        import httpx

        logger.info("Agent stopped — watching for 'Go Online' from dashboard…")
        while not self._running and not self._exiting:
            try:
                time.sleep(5)
                resp = httpx.get(
                    f"{self.config.backend_http_url}/gpus/",
                    timeout=5,
                )
                if resp.status_code == 200:
                    for gpu in resp.json():
                        if gpu.get("id") == self.config.gpu_id and gpu.get("status") == "online":
                            logger.info("GPU marked online — restarting agent")
                            self._start_agent()
                            return
            except Exception as e:
                logger.debug("Polling backend: %s", e)

    def _stop_agent(self):
        if not self._running or not self._agent:
            return

        self._running = False
        self._exiting = True  # Mark as manually stopped
        self.update_status("disconnected")

        if self._agent_loop and self._agent:
            # Schedule stop and wait briefly for graceful shutdown
            future = asyncio.run_coroutine_threadsafe(self._agent.stop(), self._agent_loop)
            try:
                future.result(timeout=3)  # Wait up to 3 seconds
            except Exception:
                pass

            # Cancel all remaining async tasks (reconnect sleeps, heartbeat, etc.)
            def _cancel_all():
                for task in asyncio.all_tasks(self._agent_loop):
                    task.cancel()
            try:
                self._agent_loop.call_soon_threadsafe(_cancel_all)
            except RuntimeError:
                pass

            # Stop the event loop
            try:
                self._agent_loop.call_soon_threadsafe(self._agent_loop.stop)
            except RuntimeError:
                pass

        # Wait for agent thread to actually finish
        if self._agent_thread and self._agent_thread.is_alive():
            self._agent_thread.join(timeout=5)

    # ──────────────────────────────────────────────
    # Menu handlers
    # ──────────────────────────────────────────────

    def _on_open_settings(self, icon=None, item=None):
        """Open the settings window."""
        def _open():
            import tkinter as tk
            if self._tk_root is None:
                self._tk_root = tk.Tk()
                self._tk_root.withdraw()

            from src.gui.settings import SettingsWindow
            SettingsWindow(self.config, on_save=self._on_settings_saved)
            self._tk_root.mainloop()

        # Run in a new thread to avoid blocking the tray
        threading.Thread(target=_open, daemon=True).start()

    def _on_settings_saved(self, new_config: "AgentConfig"):
        """Callback when settings are saved — update internal config."""
        self.config = new_config
        logger.info("Settings updated — restart agent for changes to take effect")

    def _on_open_logs(self, icon=None, item=None):
        """Open the log directory in Explorer."""
        import subprocess
        log_dir = self.config.log_dir()
        subprocess.Popen(["explorer", str(log_dir)])

    def _on_start(self, icon=None, item=None):
        self._exiting = False  # Reset manual stop flag
        self._start_agent()

    def _on_stop(self, icon=None, item=None):
        self._stop_agent()

    def _on_exit(self, icon=None, item=None):
        """Full cleanup and exit."""
        import os

        logger.info("Exit requested — shutting down")

        # 0. Hard-kill timer — guarantees process dies even if cleanup hangs
        def _force_kill():
            time.sleep(8)
            os._exit(1)
        threading.Thread(target=_force_kill, daemon=True).start()

        # 1. Stop the agent (WebSocket, heartbeat)
        self._stop_agent()

        # 2. Remove the tray icon — hide it first so Windows Shell
        #    unregisters it from the notification area immediately,
        #    then stop pystray's event loop.
        if self._icon:
            try:
                self._icon.visible = False
            except Exception:
                pass
            self._icon.stop()

        # 3. Give Windows Shell time to fully remove the icon
        #    before we kill the process (otherwise the ghost icon
        #    stays in the tray until the user hovers over it).
        time.sleep(0.5)

        # 4. Clean up tk root
        if self._tk_root:
            try:
                self._tk_root.destroy()
            except Exception:
                pass

        # 5. Force exit — daemon threads can keep the process alive
        logger.info("Goodbye!")
        os._exit(0)

