# BotRelay Cursor Plugin

BotRelay is a password manager built for AI agents. Give agents their own password vault, only the secrets they need, and the tools for secure access.

This plugin connects Cursor and Grok to **hosted MCP** at `https://api.botrelay.ai/mcp`. That server returns vault metadata and **sealed** secrets (ciphertext). It does not return plaintext. Install `botrelay-cli` on the machine that runs the agent and unlock secrets there. The vault key stays in a local file. It is never sent to the API and never placed in MCP headers.

Before using this plugin, visit [botrelay.ai](https://botrelay.ai) to create an account and set up a password vault.

This repository is the **public Cursor plugin** only. It does not contain the CLI. That package is `botrelay-cli` on PyPI. `botrelay-mcp` is deprecated and is not part of this install.

## Install

The venv and `agent.env` belong to the machine that runs the CLI. Cursor on a local Mac/PC and a Grok Bot agent do not share them. Hosted MCP auth is set per account under **Plugins → Configure**. See [Grok Bot](#grok-bot).

1. From a terminal, install the CLI:

   ```bash
   python3 -m venv ~/.venvs/botrelay
   ~/.venvs/botrelay/bin/pip install -U botrelay-cli
   ```

   On Windows the console script is `~/.venvs/botrelay/Scripts/botrelay.exe`. Activating the venv in a terminal does not change the `PATH` Cursor or Grok uses. This plugin does not launch that interpreter. Hosted MCP is a URL, not a local process.

2. Store the CLI credentials locally. The CLI prompts in the terminal. Do not paste the API key or vault key into chat:

   ```bash
   ~/.venvs/botrelay/bin/botrelay agent configure
   ```

   `botrelay agent configure` creates `~/.config/botrelay/agent.env` with mode `0600` and `KEY=VALUE` lines for:

   - `BOTRELAY_API_URL` — API URL, usually `https://api.botrelay.ai`
   - `BOTRELAY_API_KEY` — agent API key (`brt_live_…`)
   - `BOTRELAY_VAULT_KEY` — vault key (standard base64 of 32 bytes)

   Those are the only three prompts. For `botrelay` commands, this file wins over the process environment. Re-run configure to change a key. Do not expect an exported variable to override the file.

3. In Cursor **Settings**, click **Open Customize**, then **Browse Marketplace**. Find **BotRelay**, select **Install**, and choose a user or project scope.

   Until BotRelay appears in the Marketplace, use **Add Marketplace**, choose **Import from GitHub** and paste `https://github.com/botrelay-ai/botrelay-plugin`.

4. Open **Plugins → Configure** for BotRelay and set **Agent API key** (`BOTRELAY_API_KEY`, the `brt_live_…` value). Cursor sends it as `Authorization: Bearer` to `https://api.botrelay.ai/mcp`. Do not enter the vault key. Plugin config does not read `agent.env`.

   Reload the BotRelay MCP server after saving the key. Under MCPs, botrelay should show a green status with `3 tools enabled`: `get_vault`, `list_secrets`, and `get_secret`.

5. In chat, use **Try in Chat** or the `/botrelay-login` command. The prompt is: “Log into BotRelay and get the vault information.” The agent confirms `botrelay-cli` and `agent.env` on this machine, then calls hosted `get_vault`.

   During the first login, the agent checks whether `~/.venvs/botrelay/bin/botrelay` exists (including `botrelay agent decrypt`) and whether `~/.config/botrelay/agent.env` exists. It does not import `botrelay_mcp`. If `get_vault` already succeeds, it skips install and configure. Otherwise it installs with `pip install -U botrelay-cli`, runs `botrelay agent configure` (a real TTY with desktop handoff, or secure secret inputs and `--api-url`, `--api-key`, `--vault-key`), and calls `get_vault`. It reports only the vault id, name, and labels.

   **NOTE:** For a Grok Bot agent, CLI setup is performed on the shared VM, not your local machine. See [Grok Bot](#grok-bot).

## How it works

Cursor and Grok open one remote MCP connection. Tools return ciphertext and metadata. `botrelay-cli` on this machine is the only plaintext path.

```
Cursor / Grok
    |  HTTPS  https://api.botrelay.ai/mcp
    |  Authorization: Bearer agent API key
    v
Hosted MCP  (get_vault, list_secrets, get_secret)
    |
    v
sealed JSON and metadata only

This machine
    botrelay agent get <label>          fetch + decrypt
    botrelay agent decrypt < sealed     decrypt a get_secret payload
    reads ~/.config/botrelay/agent.env
    vault key stays in that file
```

`mcp.json` points at `https://api.botrelay.ai/mcp` and substitutes the plugin variable `BOTRELAY_API_KEY` into the Bearer header. It does not start a command, does not read `agent.env`, and has no vault-key field. Set the variable under **Plugins → Configure**. The Marketplace MCP entry is read-only in the dashboard; that Configure field is how the host receives the agent API key.

`get_vault` returns `id`, `name`, and `labels`. `list_secrets` returns labels and types. `get_secret` returns a sealed row (ciphertext and metadata), not a `Password`, `ApiKey`, or `Contact` dict.

Unlock on this machine:

```bash
~/.venvs/botrelay/bin/botrelay agent get <label>
```

Or pass sealed JSON from `get_secret` to the CLI, on stdin or as a file:

```bash
~/.venvs/botrelay/bin/botrelay agent decrypt sealed.json
~/.venvs/botrelay/bin/botrelay agent decrypt < sealed.json
```

Decrypt output is the typed secret. Use it in the action that needs it. Do not paste it into chat.

`scripts/launch.sh` is a retired local entrypoint. Running it exits with these instructions and does not start a server. Do not point an MCP config at it.

Internal dogfood can use `https://stage.botrelay.ai/mcp` in a private MCP config. This plugin's `mcp.json` stays on production `https://api.botrelay.ai/mcp`.

### Credential changes

Re-run `botrelay agent configure` when the API key or vault key changes. The CLI reads `agent.env` in preference to the process environment.

If the agent API key changes, also update `BOTRELAY_API_KEY` under **Plugins → Configure** and reload the BotRelay MCP server. The hosted server never sees the vault key, so a vault-key change does not require an MCP reload.

## Grok Bot

Grok Bot agents run browser tasks on a shared virtual machine. Each agent has its own desktop and browser window on that VM. They share one filesystem there, including `~/.venvs/botrelay` and `~/.config/botrelay/agent.env`. The VM is not your laptop. Cursor's `~/.venvs/botrelay` and `~/.config/botrelay/agent.env` on a local Mac/PC do not carry over. `botrelay agent configure` in Cursor on a local Mac/PC does not create `agent.env` on the Grok VM. Configuring the Grok VM does not create `agent.env` on the Mac.

For BotRelay to work for those agents:

1. Install the BotRelay plugin from the Marketplace. Until it is listed, use **Add Marketplace**, choose **Import from GitHub**, and paste `https://github.com/botrelay-ai/botrelay-plugin`.

2. Set `BOTRELAY_API_KEY` under **Plugins → Configure** for the Grok account (agent API key only). Do not enter the vault key. Reload MCP and confirm `get_vault` works. That plugin variable is account configuration, not a file on the VM.

3. On the Grok virtual machine, once, open any agent's computer (it is the same host). Check whether `~/.venvs/botrelay/bin/botrelay` can run `botrelay agent decrypt` and whether `~/.config/botrelay/agent.env` exists. If both are in place and `get_vault` or `botrelay agent vault` succeeds, stop. Skip install and configure. That one setup serves every agent on the Grok VM. They do not each install or configure.

4. If the CLI is missing, install once on that host:

   ```bash
   python3 -m venv ~/.venvs/botrelay
   ~/.venvs/botrelay/bin/pip install -U botrelay-cli
   ```

5. If `agent.env` is missing or the vault call fails, run configure on that VM. Prefer a real TTY. Hand the desktop to the user so they type the hidden prompts. Do not paste the API key or vault key into chat.

   ```bash
   ~/.venvs/botrelay/bin/botrelay agent configure
   ```

   The CLI prompts for three labels only:

   - API URL, default `https://api.botrelay.ai`
   - API key (`brt_live_…`), hidden
   - Vault key, hidden

   It writes `~/.config/botrelay/agent.env` with mode `0600`. If there is no TTY, host secure secret inputs for those three labels, then run `botrelay agent configure` with `--api-url`, `--api-key`, and `--vault-key` without echoing the values. Do not use browser form-fill tools to write `agent.env`.

After that, every agent on that Grok account can use the vault. They share the one venv and `agent.env` on the VM. Each agent decrypts with `botrelay agent decrypt` or `botrelay agent get <label>`.

Cursor on a Mac is a separate machine. The same API key and vault key are fine when both machines use the same agent vault. You are writing a second local `agent.env` on the Grok host. Set **Plugins → Configure** on the Mac account as well if that Cursor should call hosted MCP.

Browser logins on the VM are separate from your Mac/PC browser. Sites often treat the VM as a new device and ask for a one-time code.

## Troubleshooting

### MCP has no tools, or returns 401

The host is not presenting a valid agent API key. Set `BOTRELAY_API_KEY` under **Plugins → Configure** (the `brt_live_…` key only), then reload the BotRelay MCP server. Do not put the vault key in that field. `mcp.json` only contains the `${BOTRELAY_API_KEY}` placeholder.

A 401 after a key rotation means the plugin variable and `agent.env` are out of date. Update both. The plugin variable is what hosted MCP sees. `agent.env` is what the CLI uses, and the file wins over the process environment.

### `get_secret` is not a password

That is the soft-launch contract. `get_secret` returns ciphertext and metadata. Run `botrelay agent decrypt` on that JSON, or run `botrelay agent get <label>` and skip the extra step. Do not paste either result into chat.

### CLI cannot decrypt

`~/.config/botrelay/agent.env` is missing, unreadable, or the vault key does not match this vault. Run `~/.venvs/botrelay/bin/botrelay agent configure` on **this** machine. On a Grok agent, a file on the user's Mac does not count. See [Grok Bot](#grok-bot).

If `botrelay agent decrypt` is not a command, upgrade the CLI (`pip install -U botrelay-cli`). Do not install `botrelay-mcp`.

### Works in Cursor, fails in a Grok agent

A green BotRelay status in Cursor on your Mac/PC does not mean the Grok account has `BOTRELAY_API_KEY` configured, or that the Grok virtual machine has `botrelay-cli` and `~/.config/botrelay/agent.env`. Those are separate. Configuring Cursor on a Mac/PC does not create `agent.env` on the Grok VM. See [Grok Bot](#grok-bot).

## License

MIT for this plugin repository. The BotRelay product/service and related packages may use different terms.

## Support

Questions: [hello@botrelay.ai](mailto:hello@botrelay.ai).
