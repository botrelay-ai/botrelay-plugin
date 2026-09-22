# BotRelay Cursor plugin

BotRelay is a password manager built for AI agents. Give agents their own vault, only the secrets they need, and the tools for secure access.

This repository is the **public Cursor / GrokBot plugin** only.

Before using this plugin, visit [botrelay.ai](https://botrelay.ai) to create an account, setup the password vault, and obtain an API Key and Vault Key.

## Install (customers)
Whether you wish to create a password vault for Cursor Agents or GrokBot Agents, either way, you'll need to first install [Cursor](https://cursor.com/) locally and
add this plugin through the Cursor Agents window.

1. **Make the plugin available** in Cursor: Settings → Open Customize → Browse Marketplace → Add Marketplace → Import from GitHub → `https://github.com/botrelay-ai/botrelay-plugin`.
2. **Install the botrelay package** (one-time on the machine):

   ```bash
   pip install botrelay-mcp
   ```

   Or with a venv:

   ```bash
   python3 -m venv ~/.venvs/botrelay
   source ~/.venvs/botrelay/bin/activate
   pip install botrelay-mcp
   ```

3. **Add the plugin** to Cursor: Settings → Open Customize → Browse Marketplace → Filter by Personal → click the Add button to the right of BotRelay.
4. **Open the plugin** by clicking on the BotRelay plugin name from within the Cursor Marketplace. This will allow you to access the configuration settings.
5. **Configure** the plugin: from within the Cursor Marketplace with the BotRelay plugin opened, click the Configure button, and set the following values:
   - `BOTRELAY_API_URL` — default `https://api.botrelay.ai`
   - `BOTRELAY_API_KEY` — agent token (`brt_live_…`)
   - `BOTRELAY_VAULT_KEY` — base64 vault key
   - `BOTRELAY_PYTHON` — optional; use if you installed the botrelay package using a venv

6. Reload Cursor, then ask the agent to call `get_vault` or `list_secrets`.

## How it works

The plugin launches the local `botrelay-mcp` stdio server. Ciphertext is fetched from the BotRelay API and decrypted **on your machine** with the vault key. The vault key is never sent to the API.

## License

MIT for this plugin repository. The BotRelay product/service and related packages may use different terms.
