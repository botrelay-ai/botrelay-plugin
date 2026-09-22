#!/usr/bin/env bash
# Local and developer launcher for BotRelay's stdio MCP server.
# Marketplace mcp.json does not call this script. Cursor and Grok both exec
# ~/.venvs/botrelay (or BOTRELAY_PYTHON) with `python -m botrelay_mcp`.
# The botrelay_mcp package must load ~/.config/botrelay/agent.env on startup.
# This script still loads agent.env itself for local/dev runs.
# Prefer BOTRELAY_PYTHON, then a PATH console script, then ~/.venvs/botrelay,
# then a checkout venv, then python3/python. Never echo API or vault keys.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

is_missing() {
  local value="${1:-}"
  if [[ -z "$value" ]]; then
    return 0
  fi
  # Unsubstituted plugin variable (local install without real values).
  if [[ "$value" == *'${'* ]]; then
    return 0
  fi
  return 1
}

# Leading ~/ is literal when the value is quoted.
expand_tilde() {
  local value="${1:-}"
  case "$value" in
    "~/"*) printf '%s\n' "${HOME:-}/${value#"~/"}" ;;
    *) printf '%s\n' "$value" ;;
  esac
}

# Parse KEY=VALUE lines. Do not source the file: values are not expanded
# or executed. Only fill BotRelay settings that are still missing.
load_env_file() {
  local file="$1"
  local line key value
  [[ -e "$file" ]] || return 0
  if [[ ! -r "$file" ]]; then
    echo "botrelay: cannot read ${file}. Run: botrelay agent configure" >&2
    return 0
  fi
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    line="${line#"${line%%[![:space:]]*}"}"
    [[ -z "$line" || "${line:0:1}" == "#" ]] && continue
    if [[ "$line" == export[[:space:]]* ]]; then
      line="${line#export}"
      line="${line#"${line%%[![:space:]]*}"}"
    fi
    [[ "$line" == *"="* ]] || continue
    key="${line%%=*}"
    value="${line#*=}"
    key="${key%"${key##*[![:space:]]}"}"
    case "$key" in
      BOTRELAY_API_URL|BOTRELAY_API_KEY|BOTRELAY_VAULT_KEY|BOTRELAY_PYTHON) ;;
      *) continue ;;
    esac
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    if [[ ${#value} -ge 2 && "$value" == \"*\" && "$value" == *\" ]]; then
      value="${value:1:${#value}-2}"
    elif [[ ${#value} -ge 2 && "$value" == \'*\' && "$value" == *\' ]]; then
      value="${value:1:${#value}-2}"
    fi
    if is_missing "$value"; then
      continue
    fi
    if is_missing "${!key-}"; then
      # One assignment argument: the value is not expanded or executed.
      export "${key}=${value}"
    fi
  done < "$file"
}

load_agent_credentials() {
  if ! is_missing "${BOTRELAY_API_KEY:-}" && ! is_missing "${BOTRELAY_VAULT_KEY:-}" && ! is_missing "${BOTRELAY_API_URL:-}" && ! is_missing "${BOTRELAY_PYTHON:-}"; then
    return 0
  fi

  # Explicit BOTRELAY_HOME wins over the default config path for keys it sets.
  if ! is_missing "${BOTRELAY_HOME:-}"; then
    load_env_file "$(expand_tilde "${BOTRELAY_HOME%/}/agent.env")"
  fi
  if [[ -n "${HOME:-}" ]]; then
    if is_missing "${BOTRELAY_API_KEY:-}" || is_missing "${BOTRELAY_VAULT_KEY:-}" || is_missing "${BOTRELAY_API_URL:-}" || is_missing "${BOTRELAY_PYTHON:-}"; then
      load_env_file "${HOME}/.config/botrelay/agent.env"
    fi
  fi
}

load_agent_credentials

if is_missing "${BOTRELAY_API_URL:-}"; then
  export BOTRELAY_API_URL="https://api.botrelay.ai"
fi

if is_missing "${BOTRELAY_API_KEY:-}" || is_missing "${BOTRELAY_VAULT_KEY:-}"; then
  cat >&2 <<'EOF'
BOTRELAY_API_KEY and BOTRELAY_VAULT_KEY must be set for this plugin install.
They are read from the environment or from ~/.config/botrelay/agent.env (mode 0600).
If BOTRELAY_HOME is set, $BOTRELAY_HOME/agent.env is loaded as well.
Install the CLI into ~/.venvs/botrelay if needed, then run botrelay agent configure.
The CLI prompts on this machine; do not paste keys into chat:
  python3 -m venv "$HOME/.venvs/botrelay"
  "$HOME/.venvs/botrelay/bin/pip" install botrelay-mcp botrelay-cli
  "$HOME/.venvs/botrelay/bin/botrelay" agent configure
Then reload the BotRelay MCP server.
EOF
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

# Customer installs documented in the README. Shared MCP's GUI PATH is often empty.
home_venv_python() {
  local py
  for py in \
    "${HOME:-}/.venvs/botrelay/bin/python3" \
    "${HOME:-}/.venvs/botrelay/bin/python" \
    "${HOME:-}/.venvs/botrelay/Scripts/python.exe"
  do
    if [[ -x "$py" ]] && "$py" -c "import botrelay_mcp" >/dev/null 2>&1; then
      printf '%s\n' "$py"
      return 0
    fi
  done
  return 1
}

if ! is_missing "${BOTRELAY_PYTHON:-}"; then
  RESOLVED_PYTHON="$(expand_tilde "${BOTRELAY_PYTHON}")"
  if python_importable "$RESOLVED_PYTHON"; then
    exec "$RESOLVED_PYTHON" -m botrelay_mcp "$@"
  fi
fi

if MCP_CONSOLE="$(console_script)"; then
  exec "$MCP_CONSOLE" "$@"
fi

if PYTHON_BIN="$(home_venv_python)"; then
  exec "$PYTHON_BIN" -m botrelay_mcp "$@"
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
echo 'Customer install: python3 -m venv "$HOME/.venvs/botrelay" && "$HOME/.venvs/botrelay/bin/pip" install botrelay-mcp botrelay-cli' >&2
echo "Or set BOTRELAY_PYTHON to that venv's python. A GUI launch often has no botrelay-mcp on PATH." >&2
echo "Developer install: create a checkout .venv, install with pip -e, then run install-local.sh." >&2
exit 1
