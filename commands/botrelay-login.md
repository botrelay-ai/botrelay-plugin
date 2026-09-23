---
name: botrelay-login
description: Log into BotRelay and get the vault information.
---

# Log into BotRelay and get the vault information.

Set up BotRelay on the machine where this agent is running, then report the vault id, name, and labels. Grok Bot agents share one virtual machine: each agent has its own desktop and browser, and they share `~/.venvs/botrelay` and `~/.config/botrelay/agent.env`. Cursor on a Mac is a separate machine. `botrelay agent configure` in Cursor on a Mac does not create `agent.env` on the Grok VM. Configuring the Grok VM does not create `agent.env` on the Mac. One working setup serves every agent on that host.

The CLI prompts for three labels only: API URL (default `https://api.botrelay.ai`), API key (`brt_live_…`), and vault key. Do not ask for a fourth credential. Never paste an API key, vault key, or full secret JSON into chat, logs, commits, or tool arguments.

1. Check this machine. Do not print `agent.env`.

   ```bash
   ~/.venvs/botrelay/bin/python3 -c "import botrelay_mcp" && echo import-ok || echo import-missing
   test -f ~/.config/botrelay/agent.env && echo agent-env-present || echo agent-env-missing
   ```

   On Windows, `pip` and `botrelay` live under `~/.venvs/botrelay/Scripts/`, and the interpreter is `python.exe`.

2. If `import botrelay_mcp` fails, install on this machine:

   ```bash
   python3 -m venv ~/.venvs/botrelay
   ~/.venvs/botrelay/bin/pip install -U botrelay-mcp botrelay-cli
   ```

3. If `~/.config/botrelay/agent.env` is already present, reload BotRelay MCP when the server started before the file or the venv existed, then call `get_vault`. If `get_vault` succeeds, reply with only the vault `id`, `name`, and `labels`, and stop. Skip install and configure.

   If the status stays Not connected, tell the user to fully quit and reopen. Reload Window is not enough. Call `get_vault` again before configuring.

4. If `agent.env` is missing, or `get_vault` fails because the API key or vault key is missing or rejected, write credentials with the CLI. It creates `~/.config/botrelay/agent.env` (mode 0600) with `BOTRELAY_API_URL`, `BOTRELAY_API_KEY`, and `BOTRELAY_VAULT_KEY`.

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

5. After a new or updated `agent.env`, the daemon reloads the file on the next tool call when its size or mtime changes. You do not need to kill the daemon for that. Marketplace `mcp.json` does not source that file. If the shim already exited, tell the user to reload so the host launches it again. If the status stays Not connected, fully quit and reopen. Reload Window is not enough. A daemon file reload does not replace that host reconnect.

6. Call the BotRelay MCP tool `get_vault`.

7. Reply with only the vault `id`, `name`, and `labels`. Do not include secrets or ciphertext.
