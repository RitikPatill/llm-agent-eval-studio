#!/usr/bin/env bash
# Smoke-test the install path in a clean venv (no API key required).
#
# Usage: bash scripts/check_install.sh

set -e

VENV=/tmp/agenteval_check_venv

python -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"

pip install --quiet -r requirements.txt
pip install --quiet -e .

agenteval --help
agenteval run --help
agenteval serve --help

echo "Install smoke test: PASSED"

deactivate
rm -rf "$VENV"
