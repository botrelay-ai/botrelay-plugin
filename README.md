# BotRelay Cursor Plugin

BotRelay is a password manager built for AI agents. Give agents their own password vault, only the secrets they need, and the tools for secure access.

Before using this plugin, visit [botrelay.ai](https://botrelay.ai) to create an account and set up a password vault.

This repository is the **public Cursor plugin** only.

## Install

When this plugin is enabled, Cursor and Grok start the same MCP server. `botrelay_mcp` reads `~/.config/botrelay/agent.env` for the API key and vault key. Before enabling the plugin, install the `botrelay-mcp` package and run the configure step. The following walks through it:

The venv and `agent.env` belong to the machine that runs the agent. Cursor on a Mac and a Grok Bot agent do not share them. See [Grok Bot](#grok-bot).

1. From a terminal, install the MCP server and CLI:

   ```bash
   python3 -m venv ~/.venvs/botrelay
   ~/.venvs/botrelay/bin/pip install botrelay-mcp botrelay-cli
   ```

   On Windows, `pip` installs console scripts under the venv `Scripts` directory. The Marketplace entrypoint also checks `~/.venvs/botrelay/Scripts/python.exe`. Activating the venv in a terminal does not change the `PATH` Cursor or Grok uses when it starts the plugin.

2. Store the access credentials locally. The CLI prompts in the terminal. Do NOT paste the API key or vault key into chat:

   ```bash
   ~/.venvs/botrelay/bin/botrelay agent configure
   ```

   `botrelay agent configure` creates `~/.config/botrelay/agent.env` with mode `0600` and `KEY=VALUE` lines for:

   - `BOTRELAY_API_URL` — BotRelay API base URL, usually `https://api.botrelay.ai`
   - `BOTRELAY_API_KEY` — agent token (`brt_live_…`)
   - `BOTRELAY_VAULT_KEY` — base64 vault key

   The `botrelay_mcp` package must load this file when the server starts. Marketplace `mcp.json` does not source it. Values already set in the environment are left as they are. `scripts/launch.sh` (local/dev only, not the Marketplace entrypoint) also reads `$BOTRELAY_HOME/agent.env` when `BOTRELAY_HOME` is set.

3. In Cursor **Settings**, click **Open Customize**, then **Browse Marketplace**. Find **BotRelay**, select **Install**, and choose a user or project scope.

   Until BotRelay appears in the Marketplace, use **Add Marketplace**, choose **Import from GitHub** and paste `https://github.com/botrelay-ai/botrelay-plugin`.

4. Under MCPs, botrelay should have a green status with the message `3 tools enabled`. If you ran `botrelay agent configure` after enabling the plugin, turn the plugin off and on or click Reload so `botrelay_mcp` loads `agent.env`. If the status stays Not connected, or tools fail with Not connected, fully quit Cursor and reopen it. Reload Window is not enough.

5. In chat, use **Try in Chat** or the `/botrelay-login` command. The prompt is: “Log into BotRelay and get the vault information.” The agent installs the CLI into `~/.venvs/botrelay` if needed, runs `botrelay agent configure`, reloads MCP if needed, calls `get_vault`, and reports only the vault id, name, and labels.

## How it works

The plugin launches a local MCP server that agents use to open the vault. Grok and Cursor both use the same Marketplace `mcp.json`. That file starts the server with `bash -lc`, which execs `python -m botrelay_mcp` from the documented customer install (`$HOME/.venvs/botrelay`). If `BOTRELAY_PYTHON` names an interpreter that can `import botrelay_mcp`, that interpreter is used. Otherwise the command tries `$HOME/.venvs/botrelay/bin/python3`, then `…/bin/python`, then `…/Scripts/python.exe`.

`mcp.json` does not use `${CURSOR_PLUGIN_ROOT}`, `${PLUGIN_ROOT}`, or a plugin-cache path. Grok does not expand `${CURSOR_PLUGIN_ROOT}` (Cursor does), so the home-venv command does not need either host to expand a plugin root.

`mcp.json` does not source `agent.env`. The installed `botrelay_mcp` package must load `~/.config/botrelay/agent.env` (mode `0600`) on startup and must not print API or vault keys. That file holds `BOTRELAY_API_URL`, `BOTRELAY_API_KEY`, and `BOTRELAY_VAULT_KEY`.

`scripts/launch.sh` stays in this repo for local and developer launches. It is not the Marketplace entrypoint. It still loads `~/.config/botrelay/agent.env` and, when `BOTRELAY_HOME` is set, `$BOTRELAY_HOME/agent.env`, then resolves `BOTRELAY_PYTHON`, `botrelay-mcp` on `PATH`, the home venv, a checkout virtualenv, and `python3`.

The server fetches ciphertext from the BotRelay API and decrypts it on the local machine. The vault key is never transmitted, and decryption is always done locally.

## Grok Bot

Grok Bot agents run browser tasks on a shared virtual machine. Each agent has its own desktop and browser window on that VM. They share one filesystem there, including `~/.venvs/botrelay` and `~/.config/botrelay/agent.env`. The VM is not your laptop. Cursor's `~/.venvs/botrelay` and `~/.config/botrelay/agent.env` on a Mac do not carry over.

For BotRelay to work for those agents:

1. Install the BotRelay plugin from the Marketplace. Until it is listed, use **Add Marketplace**, choose **Import from GitHub**, and paste `https://github.com/botrelay-ai/botrelay-plugin`.

2. On the Grok virtual machine, once, open any agent's computer (it is the same host) and run:

   ```bash
   python3 -m venv ~/.venvs/botrelay
   ~/.venvs/botrelay/bin/pip install botrelay-mcp botrelay-cli
   ~/.venvs/botrelay/bin/botrelay agent configure
   ```

   The CLI prompts in that terminal. It writes `~/.config/botrelay/agent.env` with mode `0600`. Do not paste the API key or vault key into chat.

3. Reload the BotRelay MCP server so `botrelay_mcp` loads `agent.env`. If the status stays Not connected, fully quit and reopen. Reload Window is not enough.

After that, every agent on that Grok account can use the vault. They share the one venv and `agent.env` on the VM. They do not each install or configure.

Cursor on a Mac is a separate machine. Configuring BotRelay there does not set up Grok, and configuring the Grok VM does not set up Cursor. The same API key and vault key are fine when both machines use the same agent vault. You are writing a second local `agent.env` on the Grok host.

The plugin starts `python -m botrelay_mcp` from `~/.venvs/botrelay` on the machine that is running the agent. The `botrelay_mcp` package loads that machine's `agent.env`.

Browser logins on the VM are separate from your Mac browser. Sites often treat the VM as a new device and ask for a one-time code.

## Troubleshooting

### Not connected after Reload

After you install or reinstall the Marketplace plugin, or after writing or updating `~/.config/botrelay/agent.env`, turn botrelay off and on under MCPs or click Reload. If the status stays Not connected, or agent tools fail with Not connected, fully quit Cursor and reopen it. Reload MCP and Reload Window do not reattach the agent client to the live MCP process.

### Status flashes green, then turns red (`botrelay-mcp: not found`)

Cursor opens two connections for this plugin. Shared MCP's working directory is the open workspace, and its GUI `PATH` often has no `botrelay-mcp`. `mcp.json` does not pass secret placeholders and does not depend on that `PATH`. Credentials are loaded by `botrelay_mcp` from `agent.env`.

Grok and Cursor use the same `mcp.json` home-venv entrypoint. `bash -lc` execs `$HOME/.venvs/botrelay/bin/python3 -m botrelay_mcp` when that interpreter can `import botrelay_mcp` (then `…/bin/python` and `…/Scripts/python.exe`). If `BOTRELAY_PYTHON` names an interpreter that can import the package, that interpreter is used instead.

Do not point Marketplace `mcp.json` at a workspace-relative `./scripts/launch.sh`. Shared MCP's current directory is the workspace, so that path fails with `ENOENT`. Do not use `${PLUGIN_ROOT}` or `${CURSOR_PLUGIN_ROOT}`. Grok leaves `${CURSOR_PLUGIN_ROOT}` unsubstituted, so a plugin-cache path never starts the server there.

stderr from a failed launch names the `~/.venvs/botrelay` install and `BOTRELAY_PYTHON`. It does not include the API key or vault key.

### MCP exits before tools are listed

`BOTRELAY_API_KEY` and `BOTRELAY_VAULT_KEY` are still missing after `botrelay_mcp` loads `~/.config/botrelay/agent.env`. The MCP package must load that file on startup; this plugin's `mcp.json` does not source it. Run `~/.venvs/botrelay/bin/botrelay agent configure`, then reload the BotRelay MCP server. This plugin has no Configure variables. On a Grok agent, that file has to exist on the Grok virtual machine. See [Grok Bot](#grok-bot).

### Works in Cursor, fails in a Grok agent

A green BotRelay status in Cursor on your Mac does not mean the Grok virtual machine has `botrelay-mcp` or `~/.config/botrelay/agent.env`. Those paths are local to each machine. See [Grok Bot](#grok-bot).

## License

MIT for this plugin repository. The BotRelay product/service and related packages may use different terms.

## Support

Questions: [hello@botrelay.ai](mailto:hello@botrelay.ai).
