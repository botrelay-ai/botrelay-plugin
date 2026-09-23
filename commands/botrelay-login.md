---
name: botrelay-login
description: Log into BotRelay and get the vault information.
---

# Log into BotRelay and get the vault information.

Set up BotRelay on the machine where this agent is running, then report the vault id, name, and labels from the hosted MCP tool `get_vault`. Do not prove login by importing `botrelay_mcp`.

Grok Bot agents share one virtual machine: each agent has its own desktop and browser, and they share `~/.venvs/botrelay` and `~/.config/botrelay/agent.env`. Cursor on a Mac is a separate machine. `botrelay agent configure` in Cursor on a Mac does not create `agent.env` on the Grok VM. Configuring the Grok VM does not create `agent.env` on the Mac. One working CLI setup serves every agent on that host. Hosted MCP auth is separate: each Cursor or Grok account sets plugin variable `BOTRELAY_API_KEY` under **Plugins → Configure**.

The CLI prompts for three labels only: API URL (default `https://api.botrelay.ai`), API key (`brt_live_…`), and vault key. Do not ask for a fourth credential. Never paste an API key, vault key, sealed JSON, or full secret JSON into chat, logs, commits, or tool arguments. Never put the vault key in MCP headers or plugin variables.

1. Check this machine for `botrelay-cli`. Do not print `agent.env`. Do not import `botrelay_mcp`.

   ```bash
   test -x ~/.venvs/botrelay/bin/botrelay && echo cli-present || echo cli-missing
   ~/.venvs/botrelay/bin/botrelay agent decrypt --help >/dev/null 2>&1 && echo decrypt-ok || echo decrypt-missing
   test -f ~/.config/botrelay/agent.env && echo agent-env-present || echo agent-env-missing
   ```

   On Windows the console script is `~/.venvs/botrelay/Scripts/botrelay.exe`.

2. If the CLI is missing, or `botrelay agent decrypt` is not available, install `botrelay-cli` on this machine. Do not install `botrelay-mcp`.

   ```bash
   python3 -m venv ~/.venvs/botrelay
   ~/.venvs/botrelay/bin/pip install -U botrelay-cli
   ```

3. If `~/.config/botrelay/agent.env` is already present, call hosted MCP `get_vault`. If it succeeds, reply with only the vault `id`, `name`, and `labels`, and stop. Skip install and configure.

4. If `agent.env` is missing, or a later local `botrelay agent vault` fails because the API key or vault key is missing or rejected, write credentials with the CLI. It creates `~/.config/botrelay/agent.env` (mode 0600) with `BOTRELAY_API_URL`, `BOTRELAY_API_KEY`, and `BOTRELAY_VAULT_KEY`. For later CLI commands, that file wins over the process environment.

   Prefer interactive configure on a real TTY. On a Grok agent, run it in a terminal on the agent's desktop and hand the desktop to the user for the hidden prompts:

   ```bash
   ~/.venvs/botrelay/bin/botrelay agent configure
   ```

   The TTY prompts are `API URL [https://api.botrelay.ai]:`, hidden `API key:`, and hidden `Vault key:`. Do not ask the user to paste those values into chat. Do not read `agent.env` aloud or copy its values into the conversation.

   When there is no TTY, host secure secret inputs for those three labels, then run non-interactive configure with flags. Do not echo the values in chat, logs, or tool arguments:

   ```bash
   ~/.venvs/botrelay/bin/botrelay agent configure \
     --api-url "$BOTRELAY_API_URL" \
     --api-key "$BOTRELAY_API_KEY" \
     --vault-key "$BOTRELAY_VAULT_KEY"
   ```

   Do not use browser form-fill tools to write `agent.env`.

5. Hosted MCP will not list tools until **Plugins → Configure** has `BOTRELAY_API_KEY` (the same agent API key, `brt_live_…`). Tell the user to set that variable in the plugin UI. Do not ask them to paste it into chat. Do not put the vault key there. After they save it, reload the BotRelay MCP server so the host reconnects to `https://api.botrelay.ai/mcp` with `Authorization: Bearer`.

6. Call the BotRelay MCP tool `get_vault`. Optionally confirm the same metadata with `~/.venvs/botrelay/bin/botrelay agent vault`. Do not call `get_secret` or `botrelay agent get` during login.

7. Reply with only the vault `id`, `name`, and `labels`. Do not include secrets or ciphertext.
