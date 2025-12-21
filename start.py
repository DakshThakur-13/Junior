"""
Junior - AI Legal Assistant
Simple one-command launcher
"""
import subprocess
import sys
import os
from pathlib import Path
import time

def main():
    print("=" * 60)
    print("🎓 Starting Junior - Your AI Legal Assistant")
    print("=" * 60)
    print()
    
    project_root = Path(__file__).parent
    
    # Start backend
    print("📡 Starting Backend Server...")
    backend_cmd = [
        sys.executable, "-m", "uvicorn",
        "junior.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ]
    
    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = str(project_root / "src")
    
    backend = subprocess.Popen(
        backend_cmd,
        env=backend_env,
        cwd=str(project_root)
    )
    
    time.sleep(2)  # Give backend time to start
    
    # Start frontend
    print("🎨 Starting Frontend...")
    frontend_cmd = ["npm", "run", "dev"]
    
    frontend = subprocess.Popen(
        frontend_cmd,
        cwd=str(project_root / "frontend"),
        shell=True
    )
    
    time.sleep(2)
    
    print()
    print("=" * 60)
    print("✅ Junior is running!")
    print()
    print("   🌐 Open in browser: http://localhost:5173")
    print("   📊 API Documentation: http://localhost:8000/docs")
    print()
    print("   Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    try:
        # Wait for both processes
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        print("\n")
        print("🛑 Shutting down Junior...")
        backend.terminate()
        frontend.terminate()
        backend.wait()
        frontend.wait()
        print("✅ Stopped!")

if __name__ == "__main__":
    main()
