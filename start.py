"""
Junior - AI Legal Assistant
Single-URL launcher: builds frontend once, serves everything from FastAPI on port 8000.

  http://localhost:8000/       -> React app
  http://localhost:8000/api/   -> FastAPI
  http://localhost:8000/docs   -> Swagger UI
"""
import subprocess
import sys
import os
import shutil
import socket
import time
import atexit
from pathlib import Path
from typing import Any

psutil: Any = None
try:
    import psutil as _psutil
    psutil = _psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# ── Configuration ──────────────────────────────────────────────────────────────
PORT = 8000
STARTUP_TIMEOUT = 20   # seconds to wait for uvicorn to bind


# ── Helpers ────────────────────────────────────────────────────────────────────

def find_python(project_root: Path) -> str:
    """Return venv python if it exists, otherwise fall back to sys.executable."""
    candidates = [
        project_root / "venv"  / "Scripts" / "python.exe",   # Windows (venv)
        project_root / ".venv" / "Scripts" / "python.exe",   # Windows (.venv)
        project_root / "venv"  / "bin"     / "python",       # Linux/Mac
        project_root / ".venv" / "bin"     / "python",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return sys.executable


def is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) != 0


def free_port(port: int) -> None:
    """Kill whatever is occupying the port (requires psutil)."""
    if not HAS_PSUTIL:
        print(f"   [!] Port {port} in use. Install psutil for auto-kill, or stop it manually.")
        return
    if psutil is None:
        return
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            for conn in proc.net_connections():
                if conn.laddr.port == port:
                    print(f"   Stopping {proc.info['name']} (PID {proc.info['pid']}) on :{port}")
                    proc.terminate()
                    proc.wait(timeout=3)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            pass
    time.sleep(0.8)


def wait_for_port(port: int, timeout: int = STARTUP_TIMEOUT) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex(("localhost", port)) == 0:
                    return True
        except OSError:
            pass
        time.sleep(0.5)
    return False


def stop(*procs):
    for p in procs:
        if p is None:
            continue
        try:
            p.terminate()
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
        except Exception:
            pass


# ── Build step ─────────────────────────────────────────────────────────────────

def build_frontend(project_root: Path) -> bool:
    """Run `npm run build` inside frontend/. Returns True on success."""
    frontend_dir = project_root / "frontend"

    if not frontend_dir.exists():
        print("   [!] frontend/ directory not found — skipping build.")
        return False

    if not (shutil.which("npm") or shutil.which("npm.cmd")):
        print("   [!] npm not found. Install Node.js from https://nodejs.org/")
        return False

    # Install node_modules if missing
    if not (frontend_dir / "node_modules").exists():
        print("   Installing frontend dependencies...")
        r = subprocess.run("npm install", cwd=str(frontend_dir), shell=True)
        if r.returncode != 0:
            print("   [!] npm install failed.")
            return False

    print("   Building...")
    result = subprocess.run("npm run build", cwd=str(frontend_dir), shell=True)
    if result.returncode != 0:
        print("   [!] Frontend build failed — the app will start without a UI.")
        return False

    dist = frontend_dir / "dist" / "index.html"
    if dist.exists():
        print(f"   Build complete -> frontend/dist/")
        return True

    print("   [!] Build finished but dist/index.html not found.")
    return False


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Junior - AI Legal Assistant")
    print("=" * 60)
    print()

    project_root = Path(__file__).parent
    python_exe   = find_python(project_root)

    # 1. Build frontend
    print("[1/2] Building frontend...")
    build_frontend(project_root)
    print()

    # 2. Free port if occupied
    if not is_port_free(PORT):
        print(f"[!] Port {PORT} is in use — attempting to free it...")
        free_port(PORT)

    # 3. Start FastAPI (serves frontend + API on one port)
    print(f"[2/2] Starting server on http://localhost:{PORT} ...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")
    env["PYTHONIOENCODING"] = "utf-8"

    server = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "junior.main:app",
         "--host", "0.0.0.0",
         "--port", str(PORT),
         "--reload",
         "--reload-dir", str(project_root / "src")],
        env=env,
        cwd=str(project_root),
    )
    atexit.register(stop, server)

    if wait_for_port(PORT):
        print(f"   Ready!")
    else:
        print(f"   [!] Server did not respond within {STARTUP_TIMEOUT}s — check logs above.")

    print()
    print("=" * 60)
    print("  Junior is running!")
    print()
    print(f"  App   ->  http://localhost:{PORT}/")
    print(f"  Docs  ->  http://localhost:{PORT}/docs")
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    print()

    try:
        while True:
            if server.poll() is not None:
                print(f"\n[!] Server stopped unexpectedly (exit {server.poll()})")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        stop(server)
        print("Stopped.")


if __name__ == "__main__":
    main()
