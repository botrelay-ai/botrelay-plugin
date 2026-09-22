# BotRelay Cursor Plugin

BotRelay is a password manager built for AI agents. Give agents their own password vault, only the secrets they need, and the tools for secure access.

Before using this plugin, visit [botrelay.ai](https://botrelay.ai) to create an account and set up a password vault.

This repository is the **public Cursor plugin** only.

## Install

When this plugin is enabled Cursor starts an MCP server which expects to read `~/.config/botrelay/agent.env` to get the API Key and Vault Key values. So before enabling the plugin within the Cursor Marketplace, you must first install the `botrelay-mcp` server package and run the configure step to input the credential keys. The following will walk you through it:

1. From a terminal, install the MCP server:

   ```bash
   python3 -m venv ~/.venvs/botrelay
   ~/.venvs/botrelay/bin/pip install botrelay-mcp
   ```

   On Windows, `pip` installs console scripts under the venv `Scripts` directory. The launcher also checks `~/.venvs/botrelay/Scripts/python.exe`. Activating the venv in a terminal does not change the `PATH` Cursor uses when it starts the plugin.

2. Store the access credentials locally. The CLI prompts in the terminal. Do NOT paste the API key or vault key into chat:

   ```bash
   ~/.venvs/botrelay/bin/botrelay agent configure
   ```

   `botrelay agent configure` creates `~/.config/botrelay/agent.env` with mode `0600` and `KEY=VALUE` lines for:

   - `BOTRELAY_API_URL` — BotRelay API base URL, usually `https://api.botrelay.ai`
   - `BOTRELAY_API_KEY` — agent token (`brt_live_…`)
   - `BOTRELAY_VAULT_KEY` — base64 vault key

   If `BOTRELAY_HOME` is set, the launcher also reads `$BOTRELAY_HOME/agent.env`. Values already set in the environment are left as they are.

3. In Cursor **Settings**, click **Open Customize**, then **Browse Marketplace**. Find **BotRelay**, select **Install**, and choose a user or project scope.

   Until BotRelay appears in the Marketplace, use **Add Marketplace**, choose **Import from GitHub** and paste `https://github.com/botrelay-ai/botrelay-plugin`.

4. Under MCPs, botrelay should have a green status with the message `3 tools enabled`. If you ran `botrelay agent configure` after enabling the plugin, turn the plugin off and on or click Reload so `launch.sh` reads `agent.env`. If the status stays Not connected, or tools fail with Not connected, fully quit Cursor and reopen it. Reload Window is not enough.

5. In chat, use **Try in Chat** or the `/botrelay-login` command. The prompt is: “Log into BotRelay and get the vault information.” The agent installs the CLI into `~/.venvs/botrelay` if needed, runs `botrelay agent configure`, reloads MCP if needed, calls `get_vault`, and reports only the vault id, name, and labels.

## How it works

The plugin launches a local MCP server that agents use to open the vault. Marketplace `mcp.json` starts that server with `bash` and `${CURSOR_PLUGIN_ROOT}/scripts/launch.sh`. If `BOTRELAY_API_KEY` or `BOTRELAY_VAULT_KEY` is missing or still an unsubstituted `${...}` placeholder, `scripts/launch.sh` loads `~/.config/botrelay/agent.env` (and `$BOTRELAY_HOME/agent.env` when `BOTRELAY_HOME` is set). It parses `KEY=VALUE` lines itself and does not print API or vault keys.

`scripts/launch.sh` uses `BOTRELAY_PYTHON` when that environment variable, or `agent.env`, names a real interpreter. If that value is missing, it still looks for `botrelay-mcp` on `PATH`, then `~/.venvs/botrelay/bin/python3` (then `python` and `Scripts/python.exe`), then a checkout virtualenv, then `python3 -m botrelay_mcp`. The server fetches ciphertext from the BotRelay API and decrypts it on the local machine. The vault key is never transmitted, and decryption is always done locally.

The script derives its directory from its own path.

## Troubleshooting

### Not connected after Reload

After you install or reinstall the Marketplace plugin, or after writing or updating `~/.config/botrelay/agent.env`, turn botrelay off and on under MCPs or click Reload. If the status stays Not connected, or agent tools fail with Not connected, fully quit Cursor and reopen it. Reload MCP and Reload Window do not reattach the agent client to the live MCP process.

A reinstall can leave `CURSOR_PLUGIN_ROOT` pointed at a stale plugin cache path until that full restart.

### Status flashes green, then turns red (`botrelay-mcp: not found`)

Cursor opens two connections for this plugin. Shared MCP's working directory is the open workspace, and its GUI `PATH` often has no `botrelay-mcp`. `mcp.json` does not pass secret placeholders. Credentials come from the environment or from `agent.env`.

`mcp.json` points at the plugin script with Cursor's documented root variable:

```json
"command": "bash",
"args": ["${CURSOR_PLUGIN_ROOT}/scripts/launch.sh"]
```

Do not use a workspace-relative `./scripts/launch.sh`. Shared MCP's current directory is the workspace, so that path fails with `ENOENT`. Do not use `${PLUGIN_ROOT}`. Cursor does not expand that Agent Plugins variable in `mcp.json`; the name that expands is `${CURSOR_PLUGIN_ROOT}`.

If `BOTRELAY_PYTHON` is unset, `scripts/launch.sh` still runs `$HOME/.venvs/botrelay/bin/python3` when that file can `import botrelay_mcp` (then `…/bin/python` and `…/Scripts/python.exe`). stderr from a failed launch names `botrelay agent configure` and the `~/.venvs/botrelay` install steps, and does not include the API key or vault key.

### MCP exits before tools are listed

`BOTRELAY_API_KEY` and `BOTRELAY_VAULT_KEY` are still missing after `launch.sh` reads `~/.config/botrelay/agent.env`. Run `~/.venvs/botrelay/bin/botrelay agent configure`, then reload the BotRelay MCP server. This plugin has no Configure variables.

## License

MIT for this plugin repository. The BotRelay product/service and related packages may use different terms.

## Support

Questions: [hello@botrelay.ai](mailto:hello@botrelay.ai).
