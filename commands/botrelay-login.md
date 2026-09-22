---
name: botrelay-login
description: Log into BotRelay and get the vault information.
---

# Log into BotRelay and get the vault information.

Set up this agent's BotRelay credentials locally, then report the vault id, name, and labels. The CLI prompts on the machine. Never paste an API key, vault key, agent token, or full secret JSON into chat, logs, commits, or tool arguments.

1. Ensure the BotRelay venv exists and has the MCP server and CLI. Run:

   ```bash
   python3 -m venv ~/.venvs/botrelay
   ~/.venvs/botrelay/bin/pip install botrelay-mcp botrelay-cli
   ```

   On Windows, `pip` and `botrelay` live under `~/.venvs/botrelay/Scripts/`.

2. Write credentials with the CLI. It prompts locally and creates `~/.config/botrelay/agent.env` (mode 0600) with `BOTRELAY_API_URL`, `BOTRELAY_API_KEY`, and `BOTRELAY_VAULT_KEY`:

   ```bash
   ~/.venvs/botrelay/bin/botrelay agent configure
   ```

   If that command cannot prompt (no TTY), ask the user to run it in their own terminal. Do not ask them to paste the API key or vault key into chat. Do not read `agent.env` aloud or copy its values into the conversation.

3. If the BotRelay MCP server was already started, tell the user to reload it so `scripts/launch.sh` picks up `agent.env`. Then continue.

4. Call the BotRelay MCP tool `get_vault`.

5. Reply with only the vault `id`, `name`, and `labels`. Do not include secrets, tokens, or ciphertext.
