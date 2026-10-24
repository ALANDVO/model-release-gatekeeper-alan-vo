#!/usr/bin/env python3
"""Run backend tests."""
import subprocess
import sys
import os

os.chdir("/var/lib/alan-portfolio/workspaces/alan/model-release-gatekeeper-alan-vo")

# Create venv if not exists
if not os.path.exists(".venv"):
    subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)

# Install deps
subprocess.run([".venv/bin/pip", "install", "-r", "backend/requirements.txt"], check=True)

# Run tests
env = os.environ.copy()
env["PYTHONPATH"] = "backend"
result = subprocess.run([".venv/bin/python", "-m", "pytest", "backend/tests", "-v"], env=env)
sys.exit(result.returncode)

