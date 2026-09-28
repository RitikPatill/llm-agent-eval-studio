#!/usr/bin/env bash
# Record a demo of agenteval with asciinema.
#
# Prerequisites:
#   - ANTHROPIC_API_KEY set in your environment
#   - agenteval installed: pip install -r requirements.txt && pip install -e .
#   - asciinema installed: pip install asciinema  (or brew install asciinema)
#   - agg installed for GIF export: cargo install agg
#
# Usage:
#   asciinema rec docs/demo.cast --command 'bash scripts/record_demo.sh'
#   agg docs/demo.cast docs/demo.gif

set -e

echo "=== agenteval run tasks/sample/ ==="
sleep 1
agenteval run tasks/sample/
sleep 2

echo ""
echo "=== agenteval list ==="
sleep 1
agenteval list
sleep 2

echo ""
echo "=== agenteval serve (Ctrl-C to exit) ==="
sleep 1
# serve is interactive; demo just shows the startup message then exits
timeout 3 agenteval serve || true
