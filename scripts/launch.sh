#!/usr/bin/env bash
# Retired local launcher. Marketplace MCP is hosted HTTP.
# This script must not start a server, load agent.env, or print credentials.
set -euo pipefail

cat >&2 <<'EOF'
BotRelay Marketplace no longer starts a local MCP process.

Cursor and Grok connect to the hosted MCP endpoint:
  https://api.botrelay.ai/mcp/
Set the plugin variable BOTRELAY_API_KEY (agent API key only) under Plugins → Configure.
That value is sent as Authorization: Bearer. Do not put the vault key in plugin config or MCP headers.

Unlock sealed secrets on this machine with botrelay-cli:
  curl -LsSf https://astral.sh/uv/install.sh | sh
  uv tool install botrelay-cli
  uv tool update-shell
  botrelay agent configure
  botrelay agent decrypt
  botrelay agent get <label>

uv puts botrelay in ~/.local/bin. An existing ~/.venvs/botrelay/bin/botrelay is fine to keep using.
If uv cannot be installed:
  python3 -m venv "$HOME/.venvs/botrelay"
  "$HOME/.venvs/botrelay/bin/pip" install -U botrelay-cli

botrelay-mcp is deprecated. Do not install it for Marketplace.
EOF
exit 1
