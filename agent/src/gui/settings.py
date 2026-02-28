"""
UniGPU Agent — Settings Window
A tkinter window opened from the system tray to edit agent configuration.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Callable

from src.core.config import AgentConfig

# ─── Color palette (matches setup_wizard) ────────
BG           = "#0f0f1a"
BG_CARD      = "#1a1a2e"
FG           = "#e0e0e0"
FG_DIM       = "#888899"
ACCENT       = "#7c3aed"
ACCENT_HOVER = "#9b5de5"
ENTRY_BG     = "#252540"
BORDER       = "#333355"
SUCCESS      = "#22c55e"


class SettingsWindow:
    """
    Settings editor window. Reads the current config, lets the user
    edit values, and saves to config.json on Apply.
    """

    def __init__(self, config: AgentConfig, on_save: Optional[Callable] = None):
        self.config = config
        self.on_save = on_save

        self.win = tk.Toplevel()
        self.win.title("UniGPU Agent — Settings")
        self.win.geometry("500x560")
        self.win.resizable(True, True)
        self.win.minsize(400, 480)
        self.win.configure(bg=BG)
        self.win.grab_set()

        # Try to set icon
        try:
            from pathlib import Path
            icon = Path(__file__).parent / "assets" / "icon.ico"
            if icon.exists():
                self.win.iconbitmap(str(icon))
        except Exception:
            pass

        # Variables
        self._vars = {
            "gpu_id": tk.StringVar(value=config.gpu_id),
            "backend_http_url": tk.StringVar(value=config.backend_http_url),
            "backend_ws_url": tk.StringVar(value=config.backend_ws_url),
            "work_dir": tk.StringVar(value=config.work_dir),
            "docker_base_image": tk.StringVar(value=config.docker_base_image),
            "heartbeat_interval": tk.StringVar(value=str(config.heartbeat_interval)),
            "max_job_timeout": tk.StringVar(value=str(config.max_job_timeout)),
            "cpu_limit": tk.StringVar(value=str(config.cpu_limit)),
            "memory_limit": tk.StringVar(value=config.memory_limit),
        }

        self._build_ui()

    def _build_ui(self):
        # Title (fixed at top)
        tk.Label(self.win, text="⚙️  Agent Settings", font=("Segoe UI", 16, "bold"),
                 bg=BG, fg=FG).pack(pady=(15, 10))

        # ── Scrollable content area ──────────────────
        scroll_wrapper = tk.Frame(self.win, bg=BG)
        scroll_wrapper.pack(fill="both", expand=True, padx=25, pady=(0, 5))

        canvas = tk.Canvas(scroll_wrapper, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(scroll_wrapper, orient="vertical", command=canvas.yview)
        container = tk.Frame(canvas, bg=BG)

        container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas_window = canvas.create_window((0, 0), window=container, anchor="nw")

        # Make the inner frame stretch to canvas width
        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.win.protocol("WM_DELETE_WINDOW", lambda: (canvas.unbind_all("<MouseWheel>"), self.win.destroy()))

        # ── Fields ───────────────────────────────────
        fields = [
            ("GPU ID", "gpu_id", True),
            ("Backend HTTP URL", "backend_http_url", False),
            ("Backend WebSocket URL", "backend_ws_url", False),
            ("Work Directory", "work_dir", False),
            ("Docker Base Image", "docker_base_image", False),
            ("Heartbeat Interval (s)", "heartbeat_interval", False),
            ("Max Job Timeout (s)", "max_job_timeout", False),
            ("CPU Limit", "cpu_limit", False),
            ("Memory Limit", "memory_limit", False),
        ]

        for label_text, key, read_only in fields:
            tk.Label(container, text=label_text, font=("Segoe UI", 9, "bold"),
                     bg=BG, fg=FG, anchor="w").pack(fill="x", pady=(8, 2))
            entry = tk.Entry(
                container, textvariable=self._vars[key], font=("Consolas", 10),
                bg=ENTRY_BG, fg=FG, insertbackground=FG, relief="flat",
                highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT,
                state="readonly" if read_only else "normal",
                readonlybackground="#1a1a28",
            )
            entry.pack(fill="x", ipady=4)

        # Config file location hint
        tk.Label(container, text=f"Config: {AgentConfig.config_file_path()}",
                 font=("Segoe UI", 8), bg=BG, fg=FG_DIM, anchor="w").pack(fill="x", pady=(12, 0))

        # ── Buttons (fixed at bottom) ────────────────
        btn_frame = tk.Frame(self.win, bg=BG)
        btn_frame.pack(pady=15)

        tk.Button(btn_frame, text="Save", command=self._on_save,
                  font=("Segoe UI", 11, "bold"), bg=ACCENT, fg="white",
                  activebackground=ACCENT_HOVER, activeforeground="white",
                  relief="flat", cursor="hand2", padx=25, pady=6).pack(side="left", padx=8)

        tk.Button(btn_frame, text="Cancel", command=self.win.destroy,
                  font=("Segoe UI", 11), bg=BG_CARD, fg=FG,
                  activebackground=BORDER, activeforeground=FG,
                  relief="flat", cursor="hand2", padx=25, pady=6).pack(side="left", padx=8)

    def _on_save(self):
        try:
            new_config = AgentConfig(
                gpu_id=self._vars["gpu_id"].get(),
                backend_http_url=self._vars["backend_http_url"].get().strip(),
                backend_ws_url=self._vars["backend_ws_url"].get().strip(),
                work_dir=self._vars["work_dir"].get().strip(),
                docker_base_image=self._vars["docker_base_image"].get().strip(),
                heartbeat_interval=int(self._vars["heartbeat_interval"].get()),
                max_job_timeout=int(self._vars["max_job_timeout"].get()),
                cpu_limit=float(self._vars["cpu_limit"].get()),
                memory_limit=self._vars["memory_limit"].get().strip(),
                agent_token=self.config.agent_token,  # preserve token
                log_batch_interval=self.config.log_batch_interval,
            )
            path = new_config.save()

            if self.on_save:
                self.on_save(new_config)

            messagebox.showinfo("Saved", f"Settings saved to:\n{path}\n\nRestart the agent for changes to take effect.",
                                parent=self.win)
            self.win.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Value", str(e), parent=self.win)


def open_settings(config: AgentConfig, on_save: Optional[Callable] = None):
    """Open the settings window (requires an existing Tk root or Toplevel context)."""
    SettingsWindow(config, on_save)
