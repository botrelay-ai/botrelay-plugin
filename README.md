# BotRelay Cursor plugin

Zero-knowledge vault access for AI agents in [Cursor](https://cursor.com).

This repository is the **public Cursor plugin** only. The BotRelay service and Python packages are separate.

## Install (customers)

1. **Install this plugin** in Cursor: Plugins → Add Marketplace → Import from GitHub → `https://github.com/chouseknecht/botrelay-plugin` (or copy this folder to `~/.cursor/plugins/local/botrelay`).
2. **Install the MCP package** (one-time on the machine):

   ```bash
   pip install botrelay-mcp
   ```

   Or with a venv:

   ```bash
   python3 -m venv ~/.venvs/botrelay
   source ~/.venvs/botrelay/bin/activate
   pip install botrelay-mcp
   ```

3. **Configure** the plugin (Plugins → Configure):
   - `BOTRELAY_API_URL` — default `https://api.botrelay.ai`
   - `BOTRELAY_API_KEY` — agent token (`brt_live_…`)
   - `BOTRELAY_VAULT_KEY` — base64 vault key (never sent to the API)
   - `BOTRELAY_PYTHON` — optional; only if you need a specific Python interpreter

4. Reload Cursor, then ask the agent to call `get_vault` or `list_secrets`.

## How it works

The plugin launches the local `botrelay-mcp` stdio server. Ciphertext is fetched from the BotRelay API and decrypted **on your machine** with the vault key. The vault key is never sent to the API.

## License

MIT for this plugin repository. The BotRelay product/service and related packages may use different terms.
