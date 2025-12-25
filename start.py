"""
Junior - AI Legal Assistant
Simple one-command launcher
"""
import subprocess
import sys
import os
from pathlib import Path
import time
import socket
import shutil
import atexit

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Configuration
BACKEND_PORT = 8000
FRONTEND_PORT = 5173
BACKEND_TIMEOUT = 15
FRONTEND_TIMEOUT = 20

def find_python_executable(project_root: Path) -> str:
    """Find the best Python executable (prefer venv)."""
    venv_paths = [
        project_root / ".venv" / "Scripts" / "python.exe",  # Windows
        project_root / ".venv" / "bin" / "python",          # Linux/Mac
    ]
    
    for path in venv_paths:
        if path.exists():
            return str(path)
    
    return sys.executable

def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(('localhost', port)) == 0

def clear_port(port: int) -> bool:
    """Kill any process using the specified port."""
    if not HAS_PSUTIL:
        return False
    
    killed = False
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.net_connections():
                if conn.laddr.port == port:
                    print(f"   🔴 Stopping {proc.info['name']} (PID: {proc.info['pid']}) on port {port}")
                    proc.terminate()
                    proc.wait(timeout=3)
                    killed = True
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, psutil.TimeoutExpired):
            continue
    
    if killed:
        time.sleep(1)
    return killed

def wait_for_port(port: int, timeout: int = 30) -> bool:
    """Wait for a server to start on the specified port."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.5)
                result = sock.connect_ex(('localhost', port))
                if result == 0:
                    return True
        except (socket.timeout, OSError):
            pass
        time.sleep(0.5)
    return False

def cleanup_processes(*processes):
    """Gracefully terminate processes."""
    for proc in processes:
        if proc is None:
            continue
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        except Exception:
            pass

def start_backend(python_exe: str, project_root: Path):
    """Start the FastAPI backend server."""
    print("📡 Starting Backend Server...")
    
    cmd = [
        python_exe, "-m", "uvicorn",
        "junior.main:app",
        "--host", "0.0.0.0",
        "--port", str(BACKEND_PORT),
        "--reload"
    ]
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")
    
    process = subprocess.Popen(
        cmd,
        env=env,
        cwd=str(project_root)
    )
    
    if wait_for_port(BACKEND_PORT, timeout=BACKEND_TIMEOUT):
        print(f"   ✅ Backend ready on http://localhost:{BACKEND_PORT}")
    else:
        print(f"   ⚠️  Backend may still be starting...")
    
    return process

def start_frontend(project_root: Path):
    """Start the Vite frontend dev server."""
    print("🎨 Starting Frontend...")
    
    # Check for npm
    if not (shutil.which("npm") or shutil.which("npm.cmd")):
        print("   ❌ npm not found. Install Node.js from https://nodejs.org/")
        return None
    
    process = subprocess.Popen(
        "npm run dev",
        cwd=str(project_root / "frontend"),
        shell=True
    )
    
    if wait_for_port(FRONTEND_PORT, timeout=FRONTEND_TIMEOUT):
        print(f"   ✅ Frontend ready on http://localhost:{FRONTEND_PORT}")
    else:
        print(f"   ⚠️  Frontend may still be starting...")
    
    return process

def main():
    print("=" * 60)
    print("🎓 Starting Junior - Your AI Legal Assistant")
    print("=" * 60)
    print()
    
    project_root = Path(__file__).parent
    python_exe = find_python_executable(project_root)
    
    # Show Python being used
    if python_exe != sys.executable:
        print(f"🐍 Using virtual environment")
    
    # Clear ports
    print("🔍 Preparing ports...")
    for port in [BACKEND_PORT, FRONTEND_PORT]:
        if is_port_in_use(port):
            if HAS_PSUTIL:
                clear_port(port)
            else:
                print(f"   ⚠️  Port {port} in use (install psutil to auto-clear)")
    print()
    
    # Start services
    backend = start_backend(python_exe, project_root)
    if backend is None:
        sys.exit(1)
    
    frontend = start_frontend(project_root)
    if frontend is None:
        cleanup_processes(backend)
        sys.exit(1)
    
    # Register cleanup on exit
    atexit.register(cleanup_processes, backend, frontend)
    
    print()
    print("=" * 60)
    print("✅ Junior is running!")
    print()
    print(f"   🌐 Frontend: http://localhost:{FRONTEND_PORT}")
    print(f"   📚 API Docs: http://localhost:{BACKEND_PORT}/docs")
    print()
    print("   Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    # Monitor processes
    try:
        while True:
            if backend.poll() is not None:
                print(f"\n❌ Backend stopped unexpectedly (exit code: {backend.poll()})")
                break
            if frontend.poll() is not None:
                print(f"\n❌ Frontend stopped unexpectedly (exit code: {frontend.poll()})")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
    finally:
        cleanup_processes(backend, frontend)
        print("✅ Stopped!")

if __name__ == "__main__":
    main()
