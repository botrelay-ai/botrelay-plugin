# BotRelay Cursor plugin

BotRelay is a password manager built for AI agents. Give agents their own password vault, only the secrets they need, and the tools for secure access. Ciphertext comes from the API; decryption stays on your machine.

Before using this plugin, visit [botrelay.ai](https://botrelay.ai) to create an account, set up a password vault, and obtain an API key and a vault key.

This repository is the **public Cursor plugin** only.

## Install

Install [`botrelay-mcp`](https://pypi.org/project/botrelay-mcp/) (Python 3.11 or newer) before you enable the plugin. Cursor starts the MCP server as soon as the plugin is enabled. The marketplace launcher is a `bash -c` resolver: it does not require `botrelay-mcp` on the GUI `PATH`.

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

The plugin launches a local MCP server that agents use to open the vault. Marketplace starts that server with `bash -c`. The resolver uses `BOTRELAY_PYTHON` when that value is a real interpreter, then `~/.venvs/botrelay`, then the `botrelay-mcp` console script on `PATH`, then `python3 -m botrelay_mcp`. It does not use a plugin or workspace path. The server fetches ciphertext from the BotRelay API and decrypts it on the local machine. The vault key is never transmitted, and decryption is always done locally.

`scripts/launch.sh` stays in this repository for local development. It honors `BOTRELAY_PYTHON`, a `botrelay-mcp` console script on `PATH`, the `~/.venvs/botrelay` install, and a checkout virtualenv. It does not print API or vault keys. Published `mcp.json` does not invoke it.

## Troubleshooting

### Status flashes green, then turns red (`botrelay-mcp: not found`)

Cursor opens two connections for this plugin. The profile-scoped server receives Configure, including `BOTRELAY_PYTHON`, and connects. Shared MCP then spawns `botrelay` again. That spawn's working directory is the open workspace, its GUI `PATH` often has no `botrelay-mcp`, and it may omit `BOTRELAY_PYTHON` or pass the unsubstituted placeholder. A launcher that ended in `exec botrelay-mcp` hit `bash: exec: botrelay-mcp: not found` and the status went red.

The marketplace command does not depend on process env alone. `BOTRELAY_PYTHON` is also its own `mcp.json` argument, so Cursor can expand the Configure value in `command`/`args` when it does not inject the variable. If both are empty, the launcher still runs `~/.venvs/botrelay/bin/python3` (then `python`, then `Scripts/python.exe`) when that file can `import botrelay_mcp`.

`${CURSOR_PLUGIN_ROOT}` and a relative `scripts/launch.sh` are not used. Some hosts leave the variable unexpanded, and Shared MCP's current directory is the workspace, so a plugin-relative path does not resolve.

stderr from a failed launch names the install steps and does not include the API key or vault key.

## License

MIT for this plugin repository. The BotRelay product/service and related packages may use different terms.

## Support

Questions: [hello@botrelay.ai](mailto:hello@botrelay.ai).
