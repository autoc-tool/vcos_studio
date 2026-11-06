#!/bin/bash

# Switch to the current directory
cd "$(dirname "$0")"

CURRENT_PATH="$(pwd)"
export PATH="$CURRENT_PATH/../../.venv/bin:$PATH"
python -s "$CURRENT_PATH/configurator.py"

read -p "Press Enter to continue..."