#!/usr/bin/env bash
# The quality gates of the Midnite Solar integration, mirroring what Home
# Assistant core's own CI runs against a component:
#
#   1. pytest            the hardware-free suite (doubles only, never a socket)
#   2. spec verifiers    the register-map extractions still agree with the PDF
#   3. ruff check        core's own rule set (see .ruff.toml), pinned
#   4. ruff format       core's formatter, check mode unless --fix
#   5. codespell         spell check with `hass` whitelisted
#   6. mypy              type check AGAINST THE REAL INSTALLED HA
#                        (mypy.ini's python_executable points at the bench
#                        venv, which ships homeassistant with py.typed)
#   7. hassfest          core's own manifest/translations/config-flow
#                        validator, from the matching core checkout
#                        (skipped with a notice when it is not cloned)
#
# Tool versions mirror core's pins (ruff 0.16.8, codespell 2.4.3, mypy 2.3.1)
# and live in ../tools/lint-env. The interpreters are the workspace's pinned
# ones; override with the same-named env vars if this workspace ever moves
# (it has moved once; absolute paths are a known sin, named here).
#
#   tool/check.sh            audit everything, touch nothing
#   tool/check.sh --fix      apply ruff's fixes/format first, then audit
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LINT="${LINT_BIN:-$ROOT/../tools/lint-env/bin}"
PYTEST_PY="${PYTEST_PY:-/Users/randy/local_esphome_configs/.venv/bin/python}"
HA_PY="${HA_PY:-/Users/randy/midnite/ha-env/venv/bin/python}"
CORE="${CORE_CHECKOUT:-$ROOT/../tools/core-2026.9.3}"
FIX=0
[[ "${1:-}" == "--fix" ]] && FIX=1

step() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }
fail() { printf '\033[31mFAILED: %s\033[0m\n' "$1"; exit 1; }

cd "$ROOT"

step "pytest (hardware-free suite)"
"$PYTEST_PY" -m pytest -q || fail pytest

step "spec verifiers"
"$PYTEST_PY" ../spec/spec_check_extraction.py >/dev/null || fail "spec_check_extraction"
"$PYTEST_PY" ../spec/spec_check_selfconsistency.py >/dev/null || fail "spec_check_selfconsistency"
echo "extraction agrees; contradictions all documented"

step "ruff check"
if (( FIX )); then
  "$LINT/ruff" check --fix --silent || true
else
  "$LINT/ruff" check . || fail ruff
fi

step "ruff format"
if (( FIX )); then
  "$LINT/ruff" format -q || true
else
  "$LINT/ruff" format --check --quiet . || fail "ruff format (run: tool/check.sh --fix)"
fi

step "codespell"
"$LINT/codespell" --ignore-words-list=hass README.md custom_components tests \
  || fail codespell

step "mypy (typed against the bench's real homeassistant)"
"$LINT/mypy" || fail mypy

step "hassfest"
if [[ -d "$CORE/script/hassfest" ]]; then
  # Run the core's own validator with lint-env's tools python, borrowing the
  # bench venv's homeassistant for the imports the scripts themselves make
  # (nothing is installed anywhere; PYTHONPATH only reads).
  HA_LIBS="$("$HA_PY" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
  ( cd "$CORE" && PYTHONPATH="$CORE:$HA_LIBS" "$LINT/python" -m script.hassfest \
      --action validate \
      --integration-path "$ROOT/custom_components/midnite_solar" \
      -p manifest -p translations -p codeowners -p config_flow \
      -p dependencies -p dhcp -p integration_type ) \
    || fail hassfest
else
  echo "SKIP: no core checkout at $CORE"
  echo "  (clone once: git clone --depth 1 --branch 2026.9.3 https://github.com/home-assistant/core.git $CORE)"
fi

printf '\n\033[32mall gates green\033[0m\n'
