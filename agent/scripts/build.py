"""
UniGPU Agent — Build Script
Automates creating a standalone Windows executable using PyInstaller.

Usage:
    cd d:/UniGPU/agent
    python scripts/build.py
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# ─── Configuration ────────────────────────────────
SCRIPTS_DIR = Path(__file__).parent
AGENT_DIR = SCRIPTS_DIR.parent          # d:/UniGPU/agent
DIST_DIR = AGENT_DIR / "dist"
BUILD_DIR = AGENT_DIR / "build"
APP_NAME = "UniGPU Agent"
ENTRY_SCRIPT = AGENT_DIR / "run.py"
ICON_FILE = AGENT_DIR / "assets" / "icon.ico"


def clean():
    """Remove old build artifacts."""
    for d in [DIST_DIR, BUILD_DIR]:
        if d.exists():
            print(f"  Cleaning {d}...")
            try:
                shutil.rmtree(d)
            except PermissionError:
                print(f"  WARNING: Could not delete {d} (files may be locked).")
                print(f"  Close any running UniGPU Agent instances and try again.")

    spec_file = AGENT_DIR / f"{APP_NAME}.spec"
    if spec_file.exists():
        try:
            spec_file.unlink()
        except PermissionError:
            pass


def build():
    """Run PyInstaller to create the executable."""
    print(f"\n{'=' * 50}")
    print(f"  Building {APP_NAME}")
    print(f"{'=' * 50}\n")

    # Check PyInstaller is available
    try:
        import PyInstaller
        print(f"  PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("  ERROR: PyInstaller not found. Install with: pip install pyinstaller")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onefile",
        "--noconsole",                   # GUI mode - no console window
        "--noconfirm",                   # Overwrite output without asking
        "--clean",                       # Clean cache before building
        # Hidden imports that PyInstaller may miss
        "--hidden-import", "websockets",
        "--hidden-import", "httpx",
        "--hidden-import", "docker",
        "--hidden-import", "pynvml",
        "--hidden-import", "pystray",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "PIL.ImageDraw",
        "--hidden-import", "PIL.ImageFont",
        "--hidden-import", "dotenv",
        "--hidden-import", "pystray._win32",
        "--hidden-import", "src",
        "--hidden-import", "src.agent",
        "--hidden-import", "src.core",
        "--hidden-import", "src.core.config",
        "--hidden-import", "src.core.ws_client",
        "--hidden-import", "src.core.executor",
        "--hidden-import", "src.core.gpu_detector",
        "--hidden-import", "src.core.log_streamer",
        "--hidden-import", "src.core.uploader",
        "--hidden-import", "src.gui",
        "--hidden-import", "src.gui.tray",
        "--hidden-import", "src.gui.settings",
        "--hidden-import", "src.gui.setup_wizard",
        # Collect all sub-packages
        "--collect-submodules", "websockets",
        "--collect-submodules", "httpx",
        "--collect-submodules", "docker",
        "--collect-submodules", "pystray",
        # Bundle tkinter (C extension + Tcl/Tk data) and SSL certs
        "--hidden-import", "_tkinter",
        "--hidden-import", "tkinter",
        "--collect-binaries", "tkinter",
        "--collect-all", "certifi",
        # Custom hook to bundle Tcl/Tk data directories
        "--additional-hooks-dir", str(SCRIPTS_DIR),
        # Add data files
        "--add-data", f"{AGENT_DIR / '.env.example'};.",
    ]

    # Add icon if it exists
    if ICON_FILE.exists():
        cmd.extend(["--icon", str(ICON_FILE)])
        cmd.extend(["--add-data", f"{ICON_FILE};assets"])

    cmd.append(str(ENTRY_SCRIPT))

    print(f"  Running: {' '.join(cmd[:6])}...\n")
    result = subprocess.run(cmd, cwd=str(AGENT_DIR))

    if result.returncode != 0:
        print(f"\n  Build FAILED (exit code {result.returncode})")
        sys.exit(1)

    exe_path = DIST_DIR / f"{APP_NAME}.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n  Build SUCCESS")
        print(f"  Output: {exe_path}")
        print(f"  Size:   {size_mb:.1f} MB")
    else:
        print(f"\n  Build completed - check {DIST_DIR}")


def _bundle_tcl_tk(dist_app: Path):
    """Copy Tcl/Tk data directories and DLLs into the dist bundle."""
    internal = dist_app / "_internal"
    if not internal.exists():
        internal = dist_app  # fallback: some PyInstaller versions use flat layout

    py_dir = Path(sys.executable).parent
    dlls_dir = py_dir / "DLLs"

    try:
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        tcl_dir = Path(root.tk.eval('info library').replace('/', os.sep))
        tk_dir = Path(root.tk.eval('set tk_library').replace('/', os.sep))
        root.destroy()

        # Copy Tcl/Tk data directories
        for src, name in [(tcl_dir, "_tcl_data"), (tk_dir, "_tk_data")]:
            dest = internal / name
            if src.is_dir() and not dest.exists():
                print(f"  Bundling {name}: {src}")
                shutil.copytree(str(src), str(dest))

        # Copy _tkinter.pyd and tcl/tk DLLs from Python's DLLs directory
        for pattern in ["_tkinter*", "tcl*.dll", "tk*.dll", "zlib*.dll"]:
            for f in dlls_dir.glob(pattern):
                dest = internal / f.name
                if not dest.exists():
                    shutil.copy2(str(f), str(dest))
                    print(f"  Bundled DLL: {f.name}")

            # Also check Python root directory
            for f in py_dir.glob(pattern):
                if f.is_file():
                    dest = internal / f.name
                    if not dest.exists():
                        shutil.copy2(str(f), str(dest))
                        print(f"  Bundled DLL: {f.name}")

    except Exception as e:
        print(f"  WARNING: Could not bundle Tcl/Tk: {e}")
        print(f"  The .exe may not be able to open GUI windows.")


def main():
    if "--clean" in sys.argv:
        clean()
        print("  Cleaned build artifacts.")
        return

    clean()
    build()


if __name__ == "__main__":
    main()
