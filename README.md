# BotRelay Cursor plugin

BotRelay is a password manager built for AI agents. Give agents their own password vault, only the secrets they need, and the tools for secure access. Ciphertext comes from the API; decryption stays on your machine.

Before using this plugin, visit [botrelay.ai](https://botrelay.ai) to create an account, set up a password vault, and obtain an API key and a vault key.

This repository is the **public Cursor plugin** only.

## Install

Install `botrelay-mcp` before you add or enable the plugin. Cursor starts the MCP server as soon as the plugin is enabled. Marketplace launch runs a short `bash -c` wrapper: if Configure sets `BOTRELAY_PYTHON` to a real interpreter path, that Python runs `-m botrelay_mcp`; otherwise Cursor looks up `botrelay-mcp` on `PATH`.

1. From a terminal, install [`botrelay-mcp`](https://pypi.org/project/botrelay-mcp/) with Python 3.11 or newer:

   ```bash
   pip install botrelay-mcp
   ```

   A virtualenv is the usual approach. Install into the venv, then either set Configure’s `BOTRELAY_PYTHON` to that venv’s `python`/`python3`, or put the venv `bin` directory on `PATH` for the Cursor process (a global install also puts `botrelay-mcp` on `PATH`):

   ```bash
   python3 -m venv ~/.venvs/botrelay
   ~/.venvs/botrelay/bin/pip install botrelay-mcp
   ```

   On Windows, `pip` installs `botrelay-mcp.exe` in the venv `Scripts` directory. Prefer setting `BOTRELAY_PYTHON` to that venv’s `python.exe`, or add the `Scripts` directory to `PATH`. Activating the venv in a terminal does not change the `PATH` Cursor uses when it starts the plugin.

2. In Cursor **Settings**, click **Open Customize**, then **Browse Marketplace**. Find **BotRelay**, select **Install**, and choose a user or project scope.

   Until BotRelay appears in the Marketplace, use **Add Marketplace**, choose **Import from GitHub** and paste `https://github.com/botrelay-ai/botrelay-plugin`.

3. Open the BotRelay plugin and click **Configure**. Set:

   - `BOTRELAY_API_URL` — default `https://api.botrelay.ai`
   - `BOTRELAY_API_KEY` — agent token (`brt_live_…`)
   - `BOTRELAY_VAULT_KEY` — base64 vault key
   - `BOTRELAY_PYTHON` — optional. Absolute path to the venv’s `python`/`python3` that has `botrelay-mcp` installed, for example `~/.venvs/botrelay/bin/python3` or `C:\Users\you\.venvs\botrelay\Scripts\python.exe`. Marketplace launch uses this interpreter. If left empty, `botrelay-mcp` must be on `PATH`.

4. Under MCPs, botrelay should have a green status with the message `3 tools enabled`. If this is not the case, click on botrelay under MCPs to reveal the configuration window. Turn the plugin on and off or click Reload to cause the new configuration to take effect.

5. Test by asking a Cursor agent to use botrelay to call `get_vault` or `list_secrets`.

## How it works

The plugin launches a local MCP server that agents use to open the vault. Marketplace starts that server with `bash -c`: it prefers Configure’s `BOTRELAY_PYTHON` (`python -m botrelay_mcp`) and falls back to the `botrelay-mcp` console script on `PATH`. No plugin or workspace path is required. Cursor Marketplace's working directory is the open workspace, and some hosts leave `${CURSOR_PLUGIN_ROOT}` unexpanded, so a path-based launcher is not cross-host safe. The server fetches ciphertext from the BotRelay API and decrypts it on the local machine. The vault key is never transmitted, and decryption is always done locally.

`scripts/launch.sh` stays in this repository for local development. It still honors `BOTRELAY_PYTHON` and a checkout virtualenv. Published `mcp.json` does not invoke it.

## License

MIT for this plugin repository. The BotRelay product/service and related packages may use different terms.

## Support

Questions: [hello@botrelay.ai](mailto:hello@botrelay.ai).
