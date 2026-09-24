---
name: botrelay-secrets
description: Secure password vault for AI agents. Use when logging into BotRelay, loading vault information, calling get_vault, list_secrets, or get_secret, decrypting a sealed secret with botrelay agent decrypt, or doing one-time setup of ~/.venvs/botrelay and agent.env on the shared Grok VM. Never paste API or vault keys into chat.
---

# BotRelay secrets

Hosted MCP (streamable HTTP, `"type": "http"`) is `${API_BASE_URL}/mcp/`. `API_BASE_URL` is a plugin variable under **Plugins → Configure**. It defaults to production, so the default endpoint is `https://api.botrelay.ai/mcp/`. The server returns metadata and **sealed** secrets only. Plaintext is produced on this machine by `botrelay-cli`. The vault key never goes to the API, into MCP headers, or into plugin variables. The agent API key is sent only to the configured `API_BASE_URL`.

The install is bound to a single vault. Access secrets from this vault only for the current task. Don't hunt credentials for other bots or workflows.

## Two credentials, two places

| Secret | Where it lives | Sent to hosted MCP? |
| --- | --- | --- |
| Agent API key (`brt_live_…`) | Plugin variable `BOTRELAY_API_KEY` (**Plugins → Configure**), and `BOTRELAY_API_KEY` in `agent.env` for the CLI | Yes, as `Authorization: Bearer` only |
| Vault key | `BOTRELAY_VAULT_KEY` in `~/.config/botrelay/agent.env` only | No |

`botrelay agent configure` writes `~/.config/botrelay/agent.env` (mode 0600) with exactly three settings: `BOTRELAY_API_URL`, `BOTRELAY_API_KEY`, and `BOTRELAY_VAULT_KEY`. For the CLI, that file wins over the process environment. Marketplace `mcp.json` does not read it and does not contain the vault key.

`botrelay-mcp` is deprecated. Do not install it. Do not start a local MCP process.

## Which machine

`~/.venvs/botrelay` and `~/.config/botrelay/agent.env` belong to the machine that runs the CLI.

Grok Bot agents share one virtual machine. Each agent has its own desktop and browser on that VM. They share one filesystem, so one venv and one `agent.env` serve every agent on that Grok account. They do not each install or configure.

Cursor on a Mac is a separate machine. `botrelay agent configure` in Cursor on a Mac does not create `agent.env` on the Grok VM. Configuring the Grok VM does not create `agent.env` on the Mac. The same API key and vault key are fine on both machines. Each machine gets its own local `agent.env`.

Hosted MCP auth is per Cursor or Grok account: set `BOTRELAY_API_KEY` under **Plugins → Configure** on each account that should call hosted MCP. The key is sent to whatever `API_BASE_URL` is configured (default `https://api.botrelay.ai`, so `https://api.botrelay.ai/mcp/`). Those settings are not `agent.env`. The CLI origin is `BOTRELAY_API_URL` in `agent.env` and should match `API_BASE_URL` when both talk to the same environment.

## Log into BotRelay and get the vault information

When the user asks to log into BotRelay, get vault information, or runs `/botrelay-login`, do this on the machine where this agent is running. On a Grok agent that machine is the shared VM, not the user's Mac. Prove login with hosted `get_vault`, not by importing `botrelay_mcp`.

1. Check the home venv and the credential file. Do not print `agent.env`.

   ```bash
   test -x ~/.venvs/botrelay/bin/botrelay && echo cli-present || echo cli-missing
   ~/.venvs/botrelay/bin/botrelay agent decrypt --help >/dev/null 2>&1 && echo decrypt-ok || echo decrypt-missing
   test -f ~/.config/botrelay/agent.env && echo agent-env-present || echo agent-env-missing
   ```

   On Windows the console script is `~/.venvs/botrelay/Scripts/botrelay.exe`.

2. If `botrelay-cli` is missing, or `botrelay agent decrypt` is not available, install it on this machine. Do not install `botrelay-mcp`.

   ```bash
   python3 -m venv ~/.venvs/botrelay
   ~/.venvs/botrelay/bin/pip install -U botrelay-cli
   ```

3. If `agent.env` is already present, call hosted `get_vault`. If `get_vault` succeeds, report only `id`, `name`, and `labels`, and stop. Skip install and configure. One working CLI setup on this machine serves every agent on this host.

4. If `agent.env` is missing, or the CLI cannot read the vault because the API key or vault key is missing or rejected, write credentials with the CLI. It creates `~/.config/botrelay/agent.env` (mode 0600). The prompts and flags are these three labels only:

   - API URL — `BOTRELAY_API_URL`, default `https://api.botrelay.ai`
   - API key — `BOTRELAY_API_KEY` (`brt_live_…`)
   - Vault key — `BOTRELAY_VAULT_KEY` (standard base64 of 32 bytes)

   Do not ask for a fourth credential. The API key is the `brt_live_…` value.

   Prefer interactive `botrelay agent configure` on a real TTY:

   ```bash
   ~/.venvs/botrelay/bin/botrelay agent configure
   ```

   On a TTY the CLI prompts for `API URL [https://api.botrelay.ai]:`, then a hidden `API key:`, then a hidden `Vault key:`. On a Grok agent, run that command in a terminal on the agent's desktop and hand the desktop to the user so they type the hidden prompts. Do not ask them to paste the API key or vault key into chat. Do not read `agent.env` or repeat the values.

   When there is no TTY, host secure secret inputs for those three labels, then run non-interactive configure with flags. Do not echo the values in chat, logs, or tool arguments:

   ```bash
   ~/.venvs/botrelay/bin/botrelay agent configure \
     --api-url "$BOTRELAY_API_URL" \
     --api-key "$BOTRELAY_API_KEY" \
     --vault-key "$BOTRELAY_VAULT_KEY"
   ```

   `--yes` overwrites an existing file without a confirmation prompt. Do not use browser form-fill tools to write `agent.env`. After the file exists, CLI commands use it instead of the process environment. Re-run configure to change keys. Do not expect exported variables to override `agent.env`.

5. If hosted MCP is not connected, tell the user to set plugin variable `BOTRELAY_API_KEY` under **Plugins → Configure** (agent API key only) and reload the BotRelay MCP server. Do not ask them to paste the key into chat. Do not enter the vault key. The host then calls `${API_BASE_URL}/mcp/` (default `https://api.botrelay.ai/mcp/`) with `Authorization: Bearer`. Use an agent API key issued for that `API_BASE_URL`.

6. Call `get_vault`. Optionally confirm the same metadata with `~/.venvs/botrelay/bin/botrelay agent vault`. Do not call `botrelay agent get` during login.

7. Report only `id`, `name`, and `labels`.

## Tools

| Tool | Use it for | Returns |
| --- | --- | --- |
| `get_vault` | Confirm which vault this install can see | `id`, `name`, `labels` |
| `list_secrets` | Discover labels and types | `{ "secrets": [ { id, vault_id, label, secret_type, version } ] }` |
| `get_secret` | Fetch one sealed secret when you already need the ciphertext | A sealed row: ciphertext and metadata. Not a `Password`, `ApiKey`, or `Contact` dict |

`get_secret` does not decrypt. Plaintext is a separate local step. Prefer `list_secrets` or `get_vault` when labels are enough. Call `list_secrets` only to pick a label for the active task. Don't inventory the vault unless the user asks.

## How to use a secret

Pick one local unlock path. Both read `agent.env` on this machine. Neither sends the vault key to the API.

**Shorter path** — fetch and decrypt in one CLI call when you have a label:

```bash
~/.venvs/botrelay/bin/botrelay agent get <label>
```

**MCP path** — when you already called `get_secret` and hold the sealed JSON:

```bash
umask 077
sealed="$(mktemp)"
# Write the get_secret JSON to "$sealed". Do not print it.
~/.venvs/botrelay/bin/botrelay agent decrypt "$sealed"
rm -f "$sealed"
```

Stdin works the same way: `botrelay agent decrypt < "$sealed"`. Decrypt output is the typed secret (`Password`, `ApiKey`, or `Contact`), the same shape a local get used to return.

Then:

1. Call `list_secrets` (or `get_vault`) and pick a `label`.
2. Run `botrelay agent get <label>`, or call `get_secret` and pass that sealed JSON to `botrelay agent decrypt`.
3. Use the fields **in the tool that performs the action**: browser form fill for a site login, HTTP header, SDK client. Do not narrate the values. Browser form fill is for using a decrypted secret at a site. Do not use browser form-fill tools to write `agent.env`.
4. Delete any sealed temp file. Do not commit it.
5. If login needs a human (CAPTCHA, 2FA, magic link), stop and hand the desktop or a secure prompt back. Do not ask the user to paste the vault password into chat.

## Never do this

- Do not paste passwords, API keys, vault keys, sealed `get_secret` JSON, or decrypt output into chat, logs, commits, screenshots, or PR text.
- Do not ask the user to paste an API key (`brt_live_…`) or vault key into chat to create `agent.env` or to fill **Plugins → Configure**.
- Do not use browser form-fill tools to write `agent.env`.
- Do not dump `list_secrets` and decrypt every label “just in case.”
- Do not send `BOTRELAY_VAULT_KEY` to the BotRelay API, put it in MCP headers, or add it as a plugin variable.
- Do not install or launch `botrelay-mcp`.
- Do not fall back to `/home/box/botrelay/.env` or any shared credential file. This machine's CLI credentials are `~/.config/botrelay/agent.env` only.
- Do not treat hosted MCP as a decrypt service. It returns ciphertext and metadata. Plaintext stays in `botrelay-cli` on this machine.
- Do not configure again when `get_vault` already succeeds on this machine.

## If tools fail

- Hosted MCP missing or unauthorized: set `BOTRELAY_API_KEY` under **Plugins → Configure** (agent API key only), then reload the BotRelay MCP server. A 401 means that key is wrong or rotated, the key was issued for a different environment than `API_BASE_URL`, or the host did not send the Bearer header. Marketplace `mcp.json` must keep `"type": "http"` and the trailing slash on `${API_BASE_URL}/mcp/` (default `https://api.botrelay.ai/mcp/`). Do not edit `mcp.json` to change hosts. Update the plugin variables and re-run `botrelay agent configure` on this machine so `agent.env` matches. Do not ask the user to paste the key into chat.
- `get_secret` is not a password dict: that is expected. Run `botrelay agent decrypt` on the sealed JSON, or `botrelay agent get <label>`.
- CLI missing keys or decrypt errors: `~/.config/botrelay/agent.env` is missing, invalid, or the vault key does not match this vault (or is not standard base64 of 32 bytes). On a Grok agent, a file on the user's Mac does not count. Install `botrelay-cli` into `~/.venvs/botrelay` with `pip install -U botrelay-cli`, then run `botrelay agent configure` (TTY and desktop handoff, or secure secret inputs plus `--api-url`, `--api-key`, and `--vault-key`).
- `botrelay agent decrypt` is not a subcommand: upgrade `botrelay-cli`. Do not install `botrelay-mcp` to replace it.
