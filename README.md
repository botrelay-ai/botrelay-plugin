# BotRelay Cursor Plugin

BotRelay is a password manager built for AI agents. Give agents their own password vault, only the secrets they need, and the tools for secure access.

Before using this plugin, visit [botrelay.ai](https://botrelay.ai) to create an account and set up a password vault.

This repository is the **public Cursor plugin** only. It does not contain the MCP package. That package is `botrelay-mcp` on PyPI (`python -m botrelay_mcp`).

## Install

When this plugin is enabled, Cursor and Grok launch a short-lived **shim**. The shim speaks MCP on stdio and forwards to one long-lived local **daemon**. The daemon reads `~/.config/botrelay/agent.env` for the API key and vault key. Before enabling the plugin, install `botrelay-mcp` **0.2.0 or newer** and run the configure step. The following walks through it:

The venv and `agent.env` belong to the machine that runs the agent. Cursor on a Mac and a Grok Bot agent do not share them. See [Grok Bot](#grok-bot).

1. From a terminal, install the MCP package and CLI:

   ```bash
   python3 -m venv ~/.venvs/botrelay
   ~/.venvs/botrelay/bin/pip install -U botrelay-mcp botrelay-cli
   ```

   The shim and daemon in this README ship in `botrelay-mcp` **>=0.2.0**. After that release is on PyPI, the `-U` command above installs it. Older releases are a single process and do not start a daemon.

   On Windows, `pip` installs console scripts under the venv `Scripts` directory. The Marketplace entrypoint also checks `~/.venvs/botrelay/Scripts/python.exe`. Activating the venv in a terminal does not change the `PATH` Cursor or Grok uses when it starts the plugin. This release reaches the daemon over a Unix domain socket. Windows named pipes are not in this release.

2. Store the access credentials locally. The CLI prompts in the terminal. Do NOT paste the API key or vault key into chat:

   ```bash
   ~/.venvs/botrelay/bin/botrelay agent configure
   ```

   `botrelay agent configure` creates `~/.config/botrelay/agent.env` with mode `0600` and `KEY=VALUE` lines for:

   - `BOTRELAY_API_URL` — API URL, usually `https://api.botrelay.ai`
   - `BOTRELAY_API_KEY` — API key (`brt_live_…`)
   - `BOTRELAY_VAULT_KEY` — vault key (standard base64 of 32 bytes)

   Those are the only three prompts.

   The daemon prefers this file over the process environment and over an `env` block in `mcp.json`. Marketplace `mcp.json` does not source it and does not set those variables. `scripts/launch.sh` (local/dev only, not the Marketplace entrypoint) also reads `$BOTRELAY_HOME/agent.env` when `BOTRELAY_HOME` is set.

3. In Cursor **Settings**, click **Open Customize**, then **Browse Marketplace**. Find **BotRelay**, select **Install**, and choose a user or project scope.

   Until BotRelay appears in the Marketplace, use **Add Marketplace**, choose **Import from GitHub** and paste `https://github.com/botrelay-ai/botrelay-plugin`.

4. Under MCPs, botrelay should have a green status with the message `3 tools enabled`. The host shows connected only after the daemon is up and a vault metadata read succeeds. That read is the same path as `get_vault`, not `get_secret`. If the shim exited because `agent.env` was missing or rejected, fix the file and let the host launch the shim again (turn the plugin off and on, or click Reload). If the status stays Not connected, or tools fail with Not connected, fully quit Cursor and reopen it. Reload Window is not enough. See [Credential changes](#credential-changes).

5. In chat, use **Try in Chat** or the `/botrelay-login` command. The prompt is: “Log into BotRelay and get the vault information.” The agent will check if the local MCP server is available and access credentials have been configured, and then it will call `get_vault`.

   During the first login, the agent checks whether `~/.venvs/botrelay` can `import botrelay_mcp` and whether `~/.config/botrelay/agent.env` exists. If `get_vault` already succeeds, it skips install and configure. Otherwise it installs with `pip install -U botrelay-mcp botrelay-cli`, runs `botrelay agent configure` (a real TTY with desktop handoff, or secure secret inputs and `--api-url`, `--api-key`, `--vault-key`), reloads MCP, calls `get_vault`, and reports only the vault id, name, and labels.

   **NOTE:** For a Grok Bot agent, this process is performed on the shared VM, not your local machine. See [Grok Bot](#grok-bot).

## How it works

Cursor and Grok launch a local shim. The shim is not the whole server. It speaks MCP on stdio and forwards to one long-lived daemon per user on that machine. The shim starts the daemon when it is not already running. Many shims share that daemon. The daemon holds the credentials, calls the BotRelay API, and decrypts ciphertext locally. The vault key never leaves the daemon.

```
Cursor / Grok
    |  stdio MCP
    v
shim  (python -m botrelay_mcp, one per host connection)
    |  Unix domain socket, mode 0600
    v
daemon  (one per user; API calls and decrypt)
    |
    v
BotRelay API  (ciphertext only; vault key stays in the daemon)
```

Grok and Cursor both use the same Marketplace `mcp.json`. That file starts the shim with `bash -lc`, which execs `python -m botrelay_mcp` from the documented customer install (`$HOME/.venvs/botrelay`). If `BOTRELAY_PYTHON` names an interpreter that can `import botrelay_mcp`, that interpreter is used. Otherwise the command tries `$HOME/.venvs/botrelay/bin/python3`, then `…/bin/python`, then `…/Scripts/python.exe`.

`mcp.json` does not use `${CURSOR_PLUGIN_ROOT}`, `${PLUGIN_ROOT}`, or a plugin-cache path. Grok does not expand `${CURSOR_PLUGIN_ROOT}` (Cursor does), so the home-venv command does not need either host to expand a plugin root.

`mcp.json` does not source `agent.env`. The installed `botrelay_mcp` package must load `~/.config/botrelay/agent.env` (mode `0600`) in the daemon. The daemon prefers that file over the process environment and over `mcp.json` env. The file holds `BOTRELAY_API_URL`, `BOTRELAY_API_KEY`, and `BOTRELAY_VAULT_KEY`. The shim does not print API or vault keys.

The host shows a green, connected status only after the daemon is up and a vault metadata read succeeds (the same path as `get_vault`, not `get_secret`). If `agent.env` is missing or invalid, or the API rejects the startup read, the shim writes a precise error to stderr, exits non-zero, and leaves stdout empty. The host stays Not connected. Fix `agent.env`, then let the host relaunch the shim.

`scripts/launch.sh` stays in this repo for local and developer launches. It is not the Marketplace entrypoint. It still loads `~/.config/botrelay/agent.env` and, when `BOTRELAY_HOME` is set, `$BOTRELAY_HOME/agent.env`, then resolves `BOTRELAY_PYTHON`, `botrelay-mcp` on `PATH`, the home venv, a checkout virtualenv, and `python3`. That script execs the same `python -m botrelay_mcp` shim.

### Credential changes

Re-run `botrelay agent configure` when the API key or vault key changes. The daemon reloads `agent.env` when the file's size or mtime changes, on the next tool call. You do not need to kill the daemon for that, and you do not need to quit Cursor only to pick up a new file.

Quit and reopen when the host session itself is down. If the status stays Not connected, or tools fail with Not connected, and Reload does not fix it, fully quit Cursor or Grok and reopen it. Reload Window does not reattach the host to the stdio shim. Reloading `agent.env` inside the daemon does not replace that reconnect.

### Operators

Stop the daemon with:

```bash
~/.venvs/botrelay/bin/botrelay-mcp daemon stop
```

The next tool call starts a new daemon. On Windows the console script is `~/.venvs/botrelay/Scripts/botrelay-mcp.exe`. Stopping the daemon does not repair a host that already shows Not connected. That still needs the host to relaunch the shim, and a full quit and reopen when Reload is not enough.

`BOTRELAY_MCP_NO_DAEMON=1` is a debug-only switch. It runs the classic in-process server instead of the shim and daemon. That mode still runs the same startup vault check. Leave it unset for normal Marketplace use.

This release uses a Unix domain socket (mode `0600`). Windows named pipes are not in this release.

## Grok Bot

Grok Bot agents run browser tasks on a shared virtual machine. Each agent has its own desktop and browser window on that VM. They share one filesystem there, including `~/.venvs/botrelay` and `~/.config/botrelay/agent.env`. The VM is not your laptop. Cursor's `~/.venvs/botrelay` and `~/.config/botrelay/agent.env` on a Mac do not carry over. `botrelay agent configure` in Cursor on a Mac does not create `agent.env` on the Grok VM. Configuring the Grok VM does not create `agent.env` on the Mac.

For BotRelay to work for those agents:

1. Install the BotRelay plugin from the Marketplace. Until it is listed, use **Add Marketplace**, choose **Import from GitHub**, and paste `https://github.com/botrelay-ai/botrelay-plugin`.

2. On the Grok virtual machine, once, open any agent's computer (it is the same host). Check whether `~/.venvs/botrelay` can `import botrelay_mcp` and whether `~/.config/botrelay/agent.env` exists. If both are in place and `get_vault` succeeds, stop. Skip install and configure. That one setup serves every agent on the Grok VM. They do not each install or configure.

3. If the import fails, install once on that host. Use `botrelay-mcp` **>=0.2.0** once it is published (`pip install -U` after the release):

   ```bash
   python3 -m venv ~/.venvs/botrelay
   ~/.venvs/botrelay/bin/pip install -U botrelay-mcp botrelay-cli
   ```

4. If `agent.env` is missing or the vault call fails, run configure on that VM. Prefer a real TTY. Hand the desktop to the user so they type the hidden prompts. Do not paste the API key or vault key into chat.

   ```bash
   ~/.venvs/botrelay/bin/botrelay agent configure
   ```

   The CLI prompts for three labels only:

   - API URL, default `https://api.botrelay.ai`
   - API key (`brt_live_…`), hidden
   - Vault key, hidden

   It writes `~/.config/botrelay/agent.env` with mode `0600`. If there is no TTY, host secure secret inputs for those three labels, then run `botrelay agent configure` with `--api-url`, `--api-key`, and `--vault-key` without echoing the values. Do not use browser form-fill tools to write `agent.env`.

5. If the shim exited before tools were listed, reload the BotRelay MCP server so the host launches the shim again. A daemon that is already running reloads a changed `agent.env` on the next tool call. You do not need to kill it. If the status stays Not connected, fully quit and reopen. Reload Window is not enough.

After that, every agent on that Grok account can use the vault. They share the one venv, `agent.env`, and daemon on the VM.

Cursor on a Mac is a separate machine. The same API key and vault key are fine when both machines use the same agent vault. You are writing a second local `agent.env` on the Grok host. Each machine has its own daemon.

The plugin starts `python -m botrelay_mcp` from `~/.venvs/botrelay` on the machine that is running the agent. That process is the shim. The daemon on that machine loads that machine's `agent.env`. Marketplace `mcp.json` does not source the file.

Browser logins on the VM are separate from your Mac browser. Sites often treat the VM as a new device and ask for a one-time code.

## Troubleshooting

### Not connected after Reload

After you install or reinstall the Marketplace plugin, or after a shim that already exited, turn botrelay off and on under MCPs or click Reload so the host launches the shim again. If the status stays Not connected, or agent tools fail with Not connected, fully quit Cursor and reopen it. Reload MCP and Reload Window do not reattach the agent client to the live stdio session. The daemon reloading `agent.env` does not fix that. The same quit and reopen applies in Grok when Reload leaves the server Not connected.

### Status flashes green, then turns red (`botrelay-mcp: not found`)

Cursor opens two connections for this plugin. Shared MCP's working directory is the open workspace, and its GUI `PATH` often has no `botrelay-mcp`. `mcp.json` does not pass secret placeholders and does not depend on that `PATH`. Credentials are loaded by the daemon from `agent.env`.

Grok and Cursor use the same `mcp.json` home-venv entrypoint. `bash -lc` execs `$HOME/.venvs/botrelay/bin/python3 -m botrelay_mcp` when that interpreter can `import botrelay_mcp` (then `…/bin/python` and `…/Scripts/python.exe`). If `BOTRELAY_PYTHON` names an interpreter that can import the package, that interpreter is used instead.

Do not point Marketplace `mcp.json` at a workspace-relative `./scripts/launch.sh`. Shared MCP's current directory is the workspace, so that path fails with `ENOENT`. Do not use `${PLUGIN_ROOT}` or `${CURSOR_PLUGIN_ROOT}`. Grok leaves `${CURSOR_PLUGIN_ROOT}` unsubstituted, so a plugin-cache path never starts the server there.

stderr from a failed launch names the `~/.venvs/botrelay` install and `BOTRELAY_PYTHON`. It does not include the API key or vault key.

### MCP exits before tools are listed

The shim exits before tools are listed when startup does not succeed. That includes a missing or invalid `~/.config/botrelay/agent.env`, and an API rejection of the startup vault metadata read (the same path as `get_vault`, not `get_secret`). stderr has a precise error, stdout is empty, and the host stays Not connected. The MCP package must load that file in the daemon; this plugin's `mcp.json` does not source it. Run `~/.venvs/botrelay/bin/botrelay agent configure`, then let the host relaunch the shim. This plugin has no Configure variables. On a Grok agent, that file has to exist on the Grok virtual machine. See [Grok Bot](#grok-bot).

### Updated credentials and the daemon is still running

Re-run `botrelay agent configure`. The daemon reloads `agent.env` when the file's size or mtime changes, on the next tool call. You do not need to kill the daemon, and `botrelay-mcp daemon stop` is not required for a credential edit. Prefer `agent.env` over process environment variables and over an `env` block in `mcp.json`.

If the shim already exited, or the status stays Not connected after Reload, fully quit and reopen. A daemon file reload does not reconnect the host.

### Works in Cursor, fails in a Grok agent

A green BotRelay status in Cursor on your Mac does not mean the Grok virtual machine has `botrelay-mcp` or `~/.config/botrelay/agent.env`. Those paths are local to each machine, and so is the daemon. Configuring Cursor on a Mac does not create `agent.env` on the Grok VM. See [Grok Bot](#grok-bot).

## License

MIT for this plugin repository. The BotRelay product/service and related packages may use different terms.

## Support

Questions: [hello@botrelay.ai](mailto:hello@botrelay.ai).
