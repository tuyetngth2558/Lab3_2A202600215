#!/usr/bin/env python
"""
Simple startup script for the ReAct Agent UI
Run this to start the Streamlit web interface for the agent
"""

import subprocess
import sys
import os
from pathlib import Path

# Get the directory of this script
script_dir = Path(__file__).parent
agent_ui_path = script_dir / "src" / "agent" / "ui.py"

print("🚀 Starting ReAct Agent UI...")
print(f"📁 Opening: {agent_ui_path}")

try:
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(agent_ui_path)],
        cwd=str(script_dir)
    )
except KeyboardInterrupt:
    print("\n\n👋 Agent UI stopped.")
    sys.exit(0)
except Exception as e:
    print(f"❌ Error starting UI: {e}")
    print("\n📌 To run manually, use:")
    print(f"   streamlit run {agent_ui_path}")
    sys.exit(1)
