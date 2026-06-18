#!/bin/bash
# Maple Cold Caller Match Engine — Start Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PORT="${PORT:-8888}"

echo "================================="
echo "  Maple Cold Caller Match Engine "
echo "================================="
echo ""
echo "  Checking dependencies..."
python3 -c "import tornado" 2>/dev/null || { echo "  ERROR: tornado not installed. Run: pip install tornado"; exit 1; }
echo "  ✓ tornado found"

echo ""
echo "  Starting server on http://localhost:${PORT}"
echo "  Press Ctrl+C to stop."
echo ""

python3 app.py --port="${PORT}"
