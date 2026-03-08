#!/bin/bash

# Pulse App Launch Utility

set -e

VENV_DIR=".venv"

# Ensure logs directory exists
mkdir -p logs

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Pulse App - Circuit Health Monitoring"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ ! -d "$VENV_DIR" ]; then
    echo "⚙️  Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    echo "✓ Virtual environment created"
fi

echo "⚙️  Activating virtual environment..."
source "$VENV_DIR/bin/activate"
echo "✓ Virtual environment activated"
echo ""

echo "⚙️  Checking dependencies..."
if pip install -q -r requirements.txt; then
    echo "✓ Dependencies satisfied"
else
    echo "⚠️  Some dependencies were updated"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Launching Pulse App..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 TIP: Press 'q' to quit the application"
echo "💡 TIP: Press 'c' to connect a device"
echo "💡 TIP: Press 'ctrl+p' to open the command palette"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run the app, showing errors in console but also logging to file
python3 __main__.py 2>&1 | tee -a logs/crash.log
EXIT_CODE=${?}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Pulse App exited cleanly"
else
    echo "⚠️  Pulse App exited with code: $EXIT_CODE"
    echo "📋 Check logs/pulse.log for details"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exit $EXIT_CODE
