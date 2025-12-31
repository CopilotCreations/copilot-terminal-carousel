#!/usr/bin/env python
"""Application entry point for Copilot Terminal Carousel."""
import atexit
import os
import signal
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))


def kill_copilot_processes() -> None:
    """Kill all copilot.exe child processes spawned by this application."""
    try:
        import psutil
    except ImportError:
        # psutil not available, skip cleanup
        return

    try:
        current_process = psutil.Process()
        children = current_process.children(recursive=True)

        copilot_processes = [
            p for p in children
            if p.is_running() and "copilot" in p.name().lower()
        ]

        for proc in copilot_processes:
            try:
                proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Wait briefly for graceful termination, then force kill
        _, alive = psutil.wait_procs(copilot_processes, timeout=2)
        for proc in alive:
            try:
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass


def signal_handler(signum: int, frame: object) -> None:
    """Handle termination signals by cleaning up child processes."""
    kill_copilot_processes()
    sys.exit(0)


if __name__ == "__main__":
    # Register cleanup on normal exit
    atexit.register(kill_copilot_processes)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Windows-specific: handle CTRL+BREAK
    if sys.platform == "win32":
        signal.signal(signal.SIGBREAK, signal_handler)

    import uvicorn
    from app.config import settings

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
    )
