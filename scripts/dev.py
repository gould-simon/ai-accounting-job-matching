#!/usr/bin/env python3
"""Development server script with proper process management."""
import os
import signal
import subprocess
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


def run_server():
    """Run the development server."""
    # Kill any existing processes on the port
    subprocess.run(
        "lsof -t -i:60000 | xargs kill -9",
        shell=True,
        stderr=subprocess.DEVNULL
    )

    # Start uvicorn with reload
    process = subprocess.Popen([
        "uvicorn",
        "app.main:app",
        "--host", "localhost",
        "--port", "60000",
        "--reload",
        "--reload-delay", "1",
        "--workers", "1",
    ])

    def handle_signal(signum, frame):
        """Handle interrupt signal."""
        # Kill the process group
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        sys.exit(0)

    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        process.wait()
    except KeyboardInterrupt:
        # Kill the process group
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        sys.exit(0)


if __name__ == "__main__":
    run_server()
