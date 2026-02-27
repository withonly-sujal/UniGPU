"""
UniGPU Agent — First-Run Setup Wizard
A tkinter wizard that guides the student through initial agent setup:
  1. Welcome screen
  2. Backend URL configuration
  3. Login with existing UniGPU account
  4. Auto-detect GPU & register with backend
  5. Save config and start agent
"""

import json
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any

import httpx

from src.core.config import AgentConfig
from src.core.gpu_detector import detect_gpus

logger = logging.getLogger("unigpu.agent.setup")

# ─── Color palette ──────────────────────────────
BG           = "#0f0f1a"
BG_CARD      = "#1a1a2e"
FG           = "#e0e0e0"
FG_DIM       = "#888899"
ACCENT       = "#7c3aed"
ACCENT_HOVER = "#9b5de5"
SUCCESS      = "#22c55e"
ERROR        = "#ef4444"
ENTRY_BG     = "#252540"
BORDER       = "#333355"


class SetupWizard:
    """
    Modal wizard window for first-time agent configuration.
    Returns the completed AgentConfig or None if cancelled.
    """

    def __init__(self):
        self.result: Optional[AgentConfig] = None
        self._token: str = ""
        self._gpu_info: list = []

        self.root = tk.Tk()
        self.root.title("UniGPU Agent — Setup")
        self.root.geometry("520x620")
        self.root.minsize(480, 520)     # minimum usable size
        self.root.resizable(True, True)
        self.root.configure(bg=BG)

        # Center on screen
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - 520) // 2
        y = (sh - 620) // 2
        self.root.geometry(f"520x620+{x}+{y}")

        # Track labels that need dynamic wraplength on resize
        self._dynamic_labels: list[tk.Label] = []

        # Try to set icon
        try:
            from pathlib import Path
            icon = Path(__file__).parent / "assets" / "icon.ico"
            if icon.exists():
                self.root.iconbitmap(str(icon))
        except Exception:
            pass

        # State
        self._backend_url = tk.StringVar(value="http://localhost:8000")
        self._username = tk.StringVar()
        self._password = tk.StringVar()
        self._gpu_label = tk.StringVar(value="Not detected yet")
        self._status = tk.StringVar(value="")

        # Build pages
        self._pages: list[tk.Frame] = []
        self._current_page = 0
        self._build_welcome_page()
        self._build_login_page()
        self._build_gpu_page()
        self._build_done_page()

        self._show_page(0)

        # Bind resize event so text labels reflow dynamically
        self.root.bind("<Configure>", self._on_resize)

    def run(self) -> Optional[AgentConfig]:
        """Show the wizard. Returns AgentConfig or None."""
        self.root.mainloop()
        return self.result

    # ──────────────────────────────────────────────
    # Page builders
    # ──────────────────────────────────────────────

    def _make_page(self) -> tk.Frame:
        frame = tk.Frame(self.root, bg=BG)
        self._pages.append(frame)
        return frame

    def _show_page(self, idx: int):
        for p in self._pages:
            p.pack_forget()
        self._pages[idx].pack(fill="both", expand=True, padx=30, pady=20)
        self._current_page = idx

    def _build_welcome_page(self):
        page = self._make_page()

        tk.Label(page, text="🖥️", font=("Segoe UI Emoji", 48), bg=BG, fg=FG).pack(pady=(20, 5))
        tk.Label(page, text="Welcome to UniGPU Agent", font=("Segoe UI", 20, "bold"),
                 bg=BG, fg=FG).pack(pady=(0, 10))

        desc = (
            "This agent connects your GPU to the UniGPU network,\n"
            "allowing other students to run training jobs on it.\n\n"
            "You'll earn credits for every job your GPU completes!\n\n"
            "Let's get set up in a few quick steps."
        )
        desc_lbl = tk.Label(page, text=desc, font=("Segoe UI", 11), bg=BG, fg=FG_DIM,
                 justify="center", wraplength=440)
        desc_lbl.pack(pady=10)
        self._dynamic_labels.append(desc_lbl)

        # Backend URL
        tk.Label(page, text="Backend Server URL", font=("Segoe UI", 10, "bold"),
                 bg=BG, fg=FG, anchor="w").pack(fill="x", pady=(20, 3))
        entry = tk.Entry(page, textvariable=self._backend_url, font=("Consolas", 11),
                         bg=ENTRY_BG, fg=FG, insertbackground=FG, relief="flat",
                         highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT)
        entry.pack(fill="x", ipady=6)

        tk.Label(page, text="Ask your admin for the server URL if not localhost",
                 font=("Segoe UI", 9), bg=BG, fg=FG_DIM).pack(anchor="w", pady=(3, 0))

        self._make_nav_btn(page, "Next →", self._on_welcome_next).pack(side="bottom", pady=20)

    def _build_login_page(self):
        page = self._make_page()

        tk.Label(page, text="Sign In", font=("Segoe UI", 20, "bold"),
                 bg=BG, fg=FG).pack(pady=(30, 5))
        tk.Label(page, text="Use your UniGPU account (register at the website first)",
                 font=("Segoe UI", 10), bg=BG, fg=FG_DIM).pack(pady=(0, 20))

        # Username
        tk.Label(page, text="Username", font=("Segoe UI", 10, "bold"),
                 bg=BG, fg=FG, anchor="w").pack(fill="x", pady=(10, 3))
        tk.Entry(page, textvariable=self._username, font=("Segoe UI", 11),
                 bg=ENTRY_BG, fg=FG, insertbackground=FG, relief="flat",
                 highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT
                 ).pack(fill="x", ipady=6)

        # Password
        tk.Label(page, text="Password", font=("Segoe UI", 10, "bold"),
                 bg=BG, fg=FG, anchor="w").pack(fill="x", pady=(15, 3))
        tk.Entry(page, textvariable=self._password, show="●", font=("Segoe UI", 11),
                 bg=ENTRY_BG, fg=FG, insertbackground=FG, relief="flat",
                 highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT
                 ).pack(fill="x", ipady=6)

        # Status
        self._login_status = tk.Label(page, textvariable=self._status,
                                       font=("Segoe UI", 10), bg=BG, fg=ERROR)
        self._login_status.pack(pady=(10, 0))

        btn_frame = tk.Frame(page, bg=BG)
        btn_frame.pack(side="bottom", pady=20, fill="x")
        self._make_nav_btn(btn_frame, "← Back", lambda: self._show_page(0)).pack(side="left")
        self._make_nav_btn(btn_frame, "Sign In & Continue →", self._on_login).pack(side="right")

    def _build_gpu_page(self):
        page = self._make_page()

        tk.Label(page, text="GPU Detection", font=("Segoe UI", 20, "bold"),
                 bg=BG, fg=FG).pack(pady=(30, 10))

        # GPU info card
        card = tk.Frame(page, bg=BG_CARD, highlightthickness=1,
                        highlightbackground=BORDER)
        card.pack(fill="x", pady=10, ipady=15, ipadx=15)

        tk.Label(card, text="🎮  Detected GPU", font=("Segoe UI", 11, "bold"),
                 bg=BG_CARD, fg=ACCENT).pack(anchor="w", padx=15, pady=(10, 5))
        self._gpu_detail_label = tk.Label(card, textvariable=self._gpu_label,
                                           font=("Consolas", 10), bg=BG_CARD, fg=FG,
                                           justify="left", anchor="w", wraplength=420)
        self._dynamic_labels.append(self._gpu_detail_label)
        self._gpu_detail_label.pack(anchor="w", padx=15, pady=(0, 10))

        # Status
        self._gpu_status = tk.Label(page, textvariable=self._status,
                                     font=("Segoe UI", 10), bg=BG, fg=FG_DIM)
        self._gpu_status.pack(pady=10)

        btn_frame = tk.Frame(page, bg=BG)
        btn_frame.pack(side="bottom", pady=20, fill="x")
        self._make_nav_btn(btn_frame, "← Back", lambda: self._show_page(1)).pack(side="left")
        self._make_nav_btn(btn_frame, "Register GPU & Finish →", self._on_register_gpu).pack(side="right")

    def _build_done_page(self):
        page = self._make_page()

        tk.Label(page, text="✅", font=("Segoe UI Emoji", 48), bg=BG, fg=SUCCESS).pack(pady=(40, 5))
        tk.Label(page, text="You're All Set!", font=("Segoe UI", 22, "bold"),
                 bg=BG, fg=FG).pack(pady=(0, 10))

        done_lbl = tk.Label(page, text=(
            "Your GPU has been registered with UniGPU.\n\n"
            "The agent will now start and appear in your\n"
            "system tray. You can right-click the tray icon\n"
            "to access settings, view logs, or stop the agent."
        ), font=("Segoe UI", 11), bg=BG, fg=FG_DIM, justify="center",
                 wraplength=420)
        done_lbl.pack(pady=15)
        self._dynamic_labels.append(done_lbl)

        self._make_nav_btn(page, "Start Agent 🚀", self._on_finish).pack(pady=30)

    # ──────────────────────────────────────────────
    # Actions
    # ──────────────────────────────────────────────

    def _on_welcome_next(self):
        url = self._backend_url.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter the backend server URL.")
            return
        self._show_page(1)

    def _on_login(self):
        username = self._username.get().strip()
        password = self._password.get().strip()
        if not username or not password:
            self._status.set("Please enter username and password")
            return

        self._status.set("Signing in…")
        self.root.update()

        base_url = self._backend_url.get().strip().rstrip("/")
        try:
            resp = httpx.post(
                f"{base_url}/auth/login",
                json={"username": username, "password": password},
                timeout=15,
                verify=False,
            )

            if resp.status_code == 200:
                data = resp.json()
                self._token = data.get("access_token", data.get("token", ""))
                self._status.set("")

                # Detect GPUs and show on the next page
                self._detect_gpu()
                self._show_page(2)
            else:
                detail = ""
                try:
                    detail = resp.json().get("detail", resp.text[:100])
                except Exception:
                    detail = resp.text[:100]
                self._status.set(f"Login failed: {detail}")

        except httpx.ConnectError:
            self._status.set(f"Cannot connect to {base_url}")
        except Exception as e:
            self._status.set(f"Error: {e}")

    def _detect_gpu(self):
        try:
            self._gpu_info = detect_gpus()
            if self._gpu_info:
                gpu = self._gpu_info[0]
                self._gpu_label.set(
                    f"Name:   {gpu.get('name', 'Unknown')}\n"
                    f"VRAM:   {gpu.get('vram_mb', 0)} MB\n"
                    f"CUDA:   {gpu.get('cuda_version', 'N/A')}\n"
                    f"Driver: {gpu.get('driver_version', 'N/A')}"
                )
            else:
                self._gpu_label.set("No GPU detected (will use mock GPU for testing)")
        except Exception as e:
            self._gpu_label.set(f"Detection failed: {e}")

    def _on_register_gpu(self):
        self._status.set("Registering GPU with backend…")
        self.root.update()

        base_url = self._backend_url.get().strip().rstrip("/")

        if not self._gpu_info:
            self._status.set("No GPU detected — cannot register")
            return

        gpu = self._gpu_info[0]
        try:
            resp = httpx.post(
                f"{base_url}/gpus/register",
                json={
                    "name": gpu.get("name", "Unknown GPU"),
                    "vram_mb": gpu.get("vram_mb", 0),
                    "cuda_version": gpu.get("cuda_version", ""),
                },
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=15,
                verify=False,
            )

            if resp.status_code in (200, 201):
                data = resp.json()
                gpu_id = data.get("id", data.get("gpu_id", ""))

                # Build and save config
                config = AgentConfig(
                    gpu_id=str(gpu_id),
                    backend_ws_url=self._backend_url.get().strip().rstrip("/").replace("http", "ws", 1) + "/ws/agent",
                    backend_http_url=base_url,
                    agent_token=self._token,
                )
                config.save()
                self.result = config

                self._status.set("")
                self._show_page(3)
            else:
                detail = ""
                try:
                    detail = resp.json().get("detail", resp.text[:150])
                except Exception:
                    detail = resp.text[:150]
                self._status.set(f"Registration failed: {detail}")

        except httpx.ConnectError:
            self._status.set(f"Cannot connect to {base_url}")
        except Exception as e:
            self._status.set(f"Error: {e}")

    def _on_resize(self, event=None):
        """Recalculate wraplength for text labels when window is resized."""
        if event and event.widget == self.root:
            new_wrap = max(300, event.width - 100)  # 50px padding each side
            for lbl in self._dynamic_labels:
                try:
                    lbl.configure(wraplength=new_wrap)
                except Exception:
                    pass

    def _on_finish(self):
        self.root.destroy()

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────

    def _make_nav_btn(self, parent: tk.Widget, text: str, command) -> tk.Button:
        btn = tk.Button(
            parent, text=text, command=command,
            font=("Segoe UI", 11, "bold"),
            bg=ACCENT, fg="white", activebackground=ACCENT_HOVER,
            activeforeground="white", relief="flat", cursor="hand2",
            padx=20, pady=8,
        )
        return btn


def run_setup_wizard() -> Optional[AgentConfig]:
    """Launch the setup wizard. Returns config or None if cancelled."""
    wizard = SetupWizard()
    return wizard.run()


if __name__ == "__main__":
    cfg = run_setup_wizard()
    if cfg:
        print(f"Setup complete! Config saved to {cfg.config_file_path()}")
        print(cfg)
    else:
        print("Setup cancelled.")
