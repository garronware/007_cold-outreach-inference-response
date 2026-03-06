#!/bin/bash
# Daily reply monitor — called by launchd
# Activates venv, runs the monitor in send+log mode

PROJECT_DIR="/Users/garronware/Library/Mobile Documents/com~apple~CloudDocs/Documents/_work/_code/_agentic/007_cold-outreach-inference-response"

cd "$PROJECT_DIR/tools"
source "$PROJECT_DIR/venv/bin/activate"
python3 auto_reply_monitor.py --send --log
