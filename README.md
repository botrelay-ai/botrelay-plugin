# BotRelay Cursor plugin

BotRelay is a password manager built for AI agents. Give agents their own password vault, only the secrets they need, and the tools for secure access. Ciphertext comes from the API; decryption stays on your machine.

Before using this plugin, visit [botrelay.ai](https://botrelay.ai) to create an account, set up a password vault, and obtain an API key and a vault key.

This repository is the **public Cursor plugin** only.

## Install

Install `botrelay-mcp` before you add or enable the plugin. Cursor starts the MCP server as soon as the plugin is enabled, and that process requires `botrelay-mcp`.

1. From a terminal, install [`botrelay-mcp`](https://pypi.org/project/botrelay-mcp/) with Python 3.11 or newer:

   ```bash
   pip install botrelay-mcp
   ```

   Or with a venv:

   ```bash
   python3 -m venv ~/.venvs/botrelay
   source ~/.venvs/botrelay/bin/activate
   pip install botrelay-mcp
   ```

   On Windows, activate that venv with `Scripts\activate` (Command Prompt) or `Scripts\Activate.ps1` (PowerShell). `pip` installs `botrelay-mcp.exe` in the venv `Scripts` directory.

2. In Cursor **Settings**, click **Open Customize**, then **Browse Marketplace**. Find **BotRelay**, select **Install**, and choose a user or project scope.

   Until BotRelay appears in the Marketplace, use **Add Marketplace**, choose **Import from GitHub** and paste `https://github.com/botrelay-ai/botrelay-plugin`.

3. Open the BotRelay plugin and click **Configure**. Set:

   - `BOTRELAY_API_URL` — default `https://api.botrelay.ai`
   - `BOTRELAY_API_KEY` — agent token (`brt_live_…`)
   - `BOTRELAY_VAULT_KEY` — base64 vault key
   - `BOTRELAY_PYTHON` — optional path to the Python executable that has `botrelay-mcp` installed. On macOS or Linux, use `~/.venvs/botrelay/bin/python`. On Windows, use the venv `Scripts\python.exe` (for example `C:\Users\you\.venvs\botrelay\Scripts\python.exe`). Leave it empty when `botrelay-mcp` is already on `PATH`.

4. Under MCPs, botrelay should have a green status with the message `3 tools enabled`. If this is not the case, click on botrelay under MCPs to reveal the configuration window. Turn the plugin on and off or click Reload to cause the new configuration to take effect.

5. Test by asking a Cursor agent to use botrelay to call `get_vault` or `list_secrets`.

## How it works

The plugin launches a local MCP server that agents use to open the vault. The server fetches ciphertext from the BotRelay API and decrypts it on the local machine. The vault key is never transmitted, and decryption is always done locally.

## License

MIT for this plugin repository. The BotRelay product/service and related packages may use different terms.

## Support

Questions: [hello@botrelay.ai](mailto:hello@botrelay.ai).
