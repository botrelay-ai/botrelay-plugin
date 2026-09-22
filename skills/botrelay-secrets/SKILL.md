---
name: botrelay-secrets
description: Secure password vault for AI agents. Use when logging into BotRelay, loading vault information, calling get_vault, list_secrets, or get_secret, or doing one-time setup of ~/.venvs/botrelay and agent.env on the shared Grok VM. Never paste API or vault keys into chat.
---

# BotRelay secrets

This plugin wraps the **local** BotRelay MCP (`apps/mcp`). Ciphertext is fetched from the API and decrypted **in this process** with `BOTRELAY_VAULT_KEY`. The vault key must never be sent to `api.botrelay.ai` or any other host.

The install is bound to a single vault. Access secrets from this vault only for the current task. Don't hunt credentials for other bots or workflows.

Credentials for this machine live in `~/.config/botrelay/agent.env` (mode 0600), written by `botrelay agent configure`. The `botrelay_mcp` package loads that file on startup. Marketplace `mcp.json` does not source it. The file holds exactly three settings: `BOTRELAY_API_URL`, `BOTRELAY_API_KEY`, and `BOTRELAY_VAULT_KEY`. Local/dev `scripts/launch.sh` also reads `$BOTRELAY_HOME/agent.env` when `BOTRELAY_HOME` is set.

## Which machine

`~/.venvs/botrelay` and `~/.config/botrelay/agent.env` belong to the machine that runs the agent.

Grok Bot agents share one virtual machine. Each agent has its own desktop and browser on that VM. They share one filesystem, so one venv and one `agent.env` serve every agent on that Grok account. They do not each install or configure.

Cursor on a Mac is a separate machine. `botrelay agent configure` in Cursor on a Mac does not create `agent.env` on the Grok VM. Configuring the Grok VM does not create `agent.env` on the Mac. The same API key and vault key are fine on both machines. Each machine gets its own local `agent.env`.

Marketplace `mcp.json` starts `python -m botrelay_mcp` from `~/.venvs/botrelay` on the machine that is running the agent (or `BOTRELAY_PYTHON` when that interpreter can `import botrelay_mcp`). The `botrelay_mcp` package loads that machine's `agent.env`.

## Log into BotRelay and get the vault information

When the user asks to log into BotRelay, get vault information, or runs `/botrelay-login`, do this on the machine where this agent is running. On a Grok agent that machine is the shared VM, not the user's Mac.

1. Check the home venv and the credential file. Do not print `agent.env`.

   ```bash
   ~/.venvs/botrelay/bin/python3 -c "import botrelay_mcp" && echo import-ok || echo import-missing
   test -f ~/.config/botrelay/agent.env && echo agent-env-present || echo agent-env-missing
   ```

   On Windows the interpreter is `~/.venvs/botrelay/Scripts/python.exe`.

2. If `botrelay_mcp` does not import, install it on this machine:

   ```bash
   python3 -m venv ~/.venvs/botrelay
   ~/.venvs/botrelay/bin/pip install -U botrelay-mcp botrelay-cli
   ```

3. If `agent.env` is already present, reload BotRelay MCP when the server started before the venv or the file existed, then call `get_vault`. If `get_vault` succeeds, report only `id`, `name`, and `labels`, and stop. Skip install and configure. One working setup on this machine serves every agent on this host.

   If the status stays Not connected, tell the user to fully quit and reopen. Reload Window is not enough. Call `get_vault` again before configuring.

4. If `agent.env` is missing, or `get_vault` fails because the API key or vault key is missing or rejected, write credentials with the CLI. It creates `~/.config/botrelay/agent.env` (mode 0600). The prompts and flags are these three labels only:

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

   With no TTY, the CLI also reads `BOTRELAY_API_URL`, `BOTRELAY_API_KEY`, and `BOTRELAY_VAULT_KEY` from the environment. `--yes` overwrites an existing file without a confirmation prompt. Do not use browser form-fill tools to write `agent.env`.

5. After a new or updated `agent.env`, tell the user to reload the BotRelay MCP server so `botrelay_mcp` loads the file. Marketplace `mcp.json` does not source it. If the status stays Not connected, fully quit and reopen. Reload Window is not enough.

6. Call `get_vault`.

7. Report only `id`, `name`, and `labels`.

## Tools (same contract as `apps/mcp`)

| Tool | Use it for | Returns |
| --- | --- | --- |
| `get_vault` | Confirm which vault this install can see | `id`, `name`, `labels` |
| `list_secrets` | Discover labels/types before decrypting | `{ "secrets": [ { id, vault_id, label, secret_type, version } ] }` |
| `get_secret` | Decrypt one typed secret when you must use it | `Password` / `ApiKey` / `Contact` as a dict |

`get_secret` is **sensitive**. Call it only when a typed value is required (login field, Authorization header, shipping contact). Prefer `list_secrets` or `get_vault` when labels are enough. Call `list_secrets` only to pick a label for the active task. Don't inventory the vault unless asked by the user.

## How to use a secret

1. Call `list_secrets` (or `get_vault`) and pick a `label`.
2. Call `get_secret` with that label.
3. Use the fields **in the tool that performs the action**: browser form fill for a site login, HTTP header, SDK client. Do not narrate the values. Browser form fill is for using a decrypted secret at a site. Do not use browser form-fill tools to write `agent.env`.
4. If login needs a human (CAPTCHA, 2FA, magic link), stop and hand the desktop or a secure prompt back. Do not ask the user to paste the vault password into chat.

## Never do this

- Do not paste passwords, API keys, vault keys, or full `get_secret` JSON into chat, logs, commits, screenshots, or PR text.
- Do not ask the user to paste an API key (`brt_live_…`) or vault key into chat to create `agent.env`.
- Do not use browser form-fill tools to write `agent.env`.
- Do not dump `list_secrets` plus `get_secret` for every label “just in case.”
- Do not send `BOTRELAY_VAULT_KEY` to the BotRelay API, a hosted MCP, or another bot.
- Do not fall back to `/home/box/botrelay/.env` or any shared credential file. This machine's credentials are `~/.config/botrelay/agent.env` only.
- Do not invent a remote decrypt endpoint. There isn’t one.
- Do not configure again when `get_vault` already succeeds on this machine.

## If tools fail

- Missing keys, or `botrelay_mcp` still has no `BOTRELAY_API_KEY` / `BOTRELAY_VAULT_KEY` after startup: `~/.config/botrelay/agent.env` is missing or incomplete on **this** machine. On a Grok agent, a file on the user's Mac does not count. Install `botrelay-mcp` and `botrelay-cli` into `~/.venvs/botrelay` with `pip install -U` when `import botrelay_mcp` fails, then run `botrelay agent configure` (TTY and desktop handoff, or secure secret inputs plus `--api-url`, `--api-key`, and `--vault-key`). That writes `agent.env` (mode 0600) with the API URL, API key, and vault key. Then reload the BotRelay MCP server. Do not ask them to paste keys into chat. The MCP package must load `agent.env` itself; Marketplace `mcp.json` does not source it.
- 401 from the API: wrong or rotated API key for this vault. Run `botrelay agent configure` again on this machine.
- Decrypt errors: `BOTRELAY_VAULT_KEY` does not match this vault (or is not standard base64 of 32 bytes).
- Import / launch errors: install into this machine's venv
  (`python3 -m venv ~/.venvs/botrelay && ~/.venvs/botrelay/bin/pip install -U botrelay-mcp botrelay-cli`).
  Developers may instead install `packages/sdk-python` and `apps/mcp` in an editable checkout `.venv` and run
  `install-local.sh`. The plugin does not reimplement decryption.
