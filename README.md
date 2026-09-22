# BotRelay Cursor plugin

BotRelay is a password manager built for AI agents. Give agents their own password vault, only the secrets they need, and the tools for secure access. Ciphertext comes from the API; decryption stays on your machine.

Before using this plugin, visit [botrelay.ai](https://botrelay.ai) to create an account, set up a password vault, and obtain an API key and a vault key.

This repository is the **public Cursor plugin** only.

## Install

Install [`botrelay-mcp`](https://pypi.org/project/botrelay-mcp/) (Python 3.11 or newer) before you enable the plugin. Cursor starts the MCP server as soon as the plugin is enabled. Marketplace `mcp.json` runs `bash` with `${CURSOR_PLUGIN_ROOT}/scripts/launch.sh`. That script does not require `botrelay-mcp` on the GUI `PATH`.

1. From a terminal, install into the venv the launcher probes even when Shared MCP injects no `BOTRELAY_PYTHON` and no `PATH` entry:

   ```bash
   python3 -m venv ~/.venvs/botrelay
   ~/.venvs/botrelay/bin/pip install botrelay-mcp
   ```

   On Windows, `pip` installs `botrelay-mcp.exe` under the venv `Scripts` directory. The launcher also checks `~/.venvs/botrelay/Scripts/python.exe`. Activating the venv in a terminal does not change the `PATH` Cursor uses when it starts the plugin.

2. In Cursor **Settings**, click **Open Customize**, then **Browse Marketplace**. Find **BotRelay**, select **Install**, and choose a user or project scope.

   Until BotRelay appears in the Marketplace, use **Add Marketplace**, choose **Import from GitHub** and paste `https://github.com/botrelay-ai/botrelay-plugin`.

3. Open the BotRelay plugin and click **Configure**. Set:

   - `BOTRELAY_API_URL` — default `https://api.botrelay.ai`
   - `BOTRELAY_API_KEY` — agent token (`brt_live_…`)
   - `BOTRELAY_VAULT_KEY` — base64 vault key
   - `BOTRELAY_PYTHON` — optional. Path to the venv `python` or `python3` that has `botrelay-mcp` installed, for example `~/.venvs/botrelay/bin/python3` or `C:\Users\you\.venvs\botrelay\Scripts\python.exe`. Leave it empty when the package is in `~/.venvs/botrelay`. Set it when the venv lives somewhere else. `botrelay-mcp` on `PATH` is only a fallback; Shared MCP's GUI `PATH` often does not include it.

4. Under MCPs, botrelay should have a green status with the message `3 tools enabled`. If this is not the case, click on botrelay under MCPs to reveal the configuration window. Turn the plugin on and off or click Reload to cause the new configuration to take effect.

5. Test by asking a Cursor agent to use botrelay to call `get_vault` or `list_secrets`.

## How it works

The plugin launches a local MCP server that agents use to open the vault. Marketplace `mcp.json` starts that server with `bash` and `${CURSOR_PLUGIN_ROOT}/scripts/launch.sh`. `scripts/launch.sh` uses `BOTRELAY_PYTHON` when Configure supplies a real interpreter. If that value is missing, it still looks for `botrelay-mcp` on `PATH`, then `~/.venvs/botrelay/bin/python3` (then `python` and `Scripts/python.exe`), then a checkout virtualenv, then `python3 -m botrelay_mcp`. The server fetches ciphertext from the BotRelay API and decrypts it on the local machine. The vault key is never transmitted, and decryption is always done locally.

The script derives its directory from its own path and does not print API or vault keys.

## Troubleshooting

### Status flashes green, then turns red (`botrelay-mcp: not found`)

Cursor opens two connections for this plugin. The profile-scoped server receives Configure, including `BOTRELAY_PYTHON`, and connects. Shared MCP then spawns `botrelay` again. That spawn's working directory is the open workspace, its GUI `PATH` often has no `botrelay-mcp`, and it may omit `BOTRELAY_PYTHON` or pass the unsubstituted placeholder. A launcher that ended in `exec botrelay-mcp` hit `bash: exec: botrelay-mcp: not found` and the status went red.

`mcp.json` points at the plugin script with Cursor's documented root variable:

```json
"command": "bash",
"args": ["${CURSOR_PLUGIN_ROOT}/scripts/launch.sh"]
```

Do not use a workspace-relative `./scripts/launch.sh`. Shared MCP's current directory is the workspace, so that path fails with `ENOENT`. Do not use `${PLUGIN_ROOT}`. Cursor does not expand that Agent Plugins variable in `mcp.json`; the name that expands is `${CURSOR_PLUGIN_ROOT}`.

If Shared MCP does not inject `BOTRELAY_PYTHON`, `scripts/launch.sh` still runs `$HOME/.venvs/botrelay/bin/python3` when that file can `import botrelay_mcp` (then `…/bin/python` and `…/Scripts/python.exe`). stderr from a failed launch names the install steps and does not include the API key or vault key.

## License

MIT for this plugin repository. The BotRelay product/service and related packages may use different terms.

## Support

Questions: [hello@botrelay.ai](mailto:hello@botrelay.ai).
