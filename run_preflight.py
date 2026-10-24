#!/usr/bin/env python3
import subprocess
import sys
import os

os.chdir("/var/lib/alan-portfolio/workspaces/alan/model-release-gatekeeper-alan-vo")
result = subprocess.run([sys.executable, "/opt/alan-portfolio/skills/github/scripts/preflight.py", ".", "--account", "alan"])
sys.exit(result.returncode)
