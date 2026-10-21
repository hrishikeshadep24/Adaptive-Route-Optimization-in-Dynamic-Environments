#!/usr/bin/env python3
"""Launcher script for Adaptive Route Optimization Research Dashboard.

Usage:
    python scripts/run_dashboard.py [--port 8501]
"""

from __future__ import annotations
import argparse
import os
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch Research Demonstrator Dashboard.")
    parser.add_argument("--port", type=int, default=8501, help="Port to run Streamlit on (default: 8501)")
    args = parser.parse_args()

    app_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "src", "adaptive_route_optimization", "ui", "app.py")
    )

    if not os.path.exists(app_path):
        print(f"Error: app.py not found at {app_path}")
        return 1

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        app_path,
        "--server.port",
        str(args.port),
        "--server.headless",
        "true",
    ]

    print(f"Launching Streamlit dashboard: {' '.join(cmd)}")
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
