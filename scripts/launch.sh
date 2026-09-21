#!/usr/bin/env bash
# Launch BotRelay's local stdio MCP server.
# Prefer the installed PyPI console script; developers can use a checkout venv.
# Cursor / Grok Bot should exec this with plugin setup env already injected.
# Never echo BOTRELAY_API_KEY or BOTRELAY_VAULT_KEY.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

is_missing() {
  local value="${1:-}"
  if [[ -z "$value" ]]; then
    return 0
  fi
  # Unsubstituted plugin variable (local install without Configure values).
  if [[ "$value" == *'${'* ]]; then
    return 0
  fi
  return 1
}

if is_missing "${BOTRELAY_API_URL:-}"; then
  export BOTRELAY_API_URL="https://api.botrelay.ai"
fi

if is_missing "${BOTRELAY_API_KEY:-}" || is_missing "${BOTRELAY_VAULT_KEY:-}"; then
  echo "BOTRELAY_API_KEY and BOTRELAY_VAULT_KEY must be set for this plugin install." >&2
  echo "Configure them on this agent/account (Plugins → Configure)." >&2
  exit 1
fi

resolve_repo_root() {
  local candidate
  if [[ -f "${PLUGIN_ROOT}/.repo-root" ]]; then
    candidate="$(tr -d '[:space:]' < "${PLUGIN_ROOT}/.repo-root")"
    if [[ -d "${candidate}/apps/mcp/src/botrelay_mcp" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  fi
  return 1
}

python_importable() {
  local py="$1"
  if [[ ! -x "$py" ]] && ! command -v "$py" >/dev/null 2>&1; then
    return 1
  fi
  "$py" -c "import botrelay_mcp, botrelay, mcp" >/dev/null 2>&1
}

console_script() {
  local script shebang interpreter
  script="$(command -v botrelay-mcp 2>/dev/null)" || return 1
  [[ -f "$script" && -x "$script" ]] || return 1
  IFS= read -r shebang < "$script" || return 1
  [[ "$shebang" == '#!'* ]] || return 1
  shebang="${shebang#\#!}"
  read -r interpreter _ <<< "$shebang"
  if [[ "$interpreter" == "/usr/bin/env" ]]; then
    read -r interpreter _ <<< "${shebang#"/usr/bin/env "}"
  fi
  [[ -n "$interpreter" ]] && python_importable "$interpreter" || return 1
  printf '%s\n' "$script"
}

checkout_python() {
  local py
  REPO_ROOT="$(resolve_repo_root)" || return 1
  for py in "${REPO_ROOT}/.venv/bin/python" "${REPO_ROOT}/.venv/bin/python3"; do
    if python_importable "$py"; then
      printf '%s\n' "$py"
      return 0
    fi
  done
  return 1
}

if ! is_missing "${BOTRELAY_PYTHON:-}" && python_importable "${BOTRELAY_PYTHON}"; then
  exec "${BOTRELAY_PYTHON}" -m botrelay_mcp "$@"
fi

if MCP_CONSOLE="$(console_script)"; then
  exec "$MCP_CONSOLE" "$@"
fi

if PYTHON_BIN="$(checkout_python)"; then
  exec "$PYTHON_BIN" -m botrelay_mcp "$@"
fi

for PYTHON_BIN in python3 python; do
  if python_importable "$PYTHON_BIN"; then
    exec "$PYTHON_BIN" -m botrelay_mcp "$@"
  fi
done

echo "botrelay-mcp is not importable." >&2
echo "Customer install: python3 -m pip install botrelay-mcp" >&2
echo "Developer install: create a checkout .venv, install with pip -e, then run install-local.sh." >&2
exit 1
