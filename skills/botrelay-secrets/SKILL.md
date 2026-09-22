---
name: botrelay-secrets
description: Secure password vault for AI agents. Use when logging into BotRelay, loading vault information, or calling get_vault, list_secrets, or get_secret. Never paste API or vault keys into chat.
---

# BotRelay secrets

This plugin wraps the **local** BotRelay MCP (`apps/mcp`). Ciphertext is fetched from the API and decrypted **in this process** with `BOTRELAY_VAULT_KEY`. The vault key must never be sent to `api.botrelay.ai` or any other host.

The install is bound to a single vault. Access secrets from this vault only for the current task. Don't hunt credentials for other bots or workflows.

Credentials for this install live in `~/.config/botrelay/agent.env` (mode 0600), written by `botrelay agent configure`. The `botrelay_mcp` package loads that file on startup. Marketplace `mcp.json` does not source it. The file holds `BOTRELAY_API_URL`, `BOTRELAY_API_KEY`, and `BOTRELAY_VAULT_KEY`. Local/dev `scripts/launch.sh` also reads `$BOTRELAY_HOME/agent.env` when `BOTRELAY_HOME` is set.

## Log into BotRelay and get the vault information

When the user asks to log into BotRelay, get vault information, or runs `/botrelay-login`:

1. Ensure `~/.venvs/botrelay` exists and has the packages:

   ```bash
   python3 -m venv ~/.venvs/botrelay
   ~/.venvs/botrelay/bin/pip install botrelay-mcp botrelay-cli
   ```

2. Run `~/.venvs/botrelay/bin/botrelay agent configure`. The CLI prompts on the user's machine and writes `~/.config/botrelay/agent.env` (mode 0600). If it cannot prompt, ask the user to run that command in their terminal. Never ask them to paste `BOTRELAY_API_KEY` or `BOTRELAY_VAULT_KEY` into chat, and never print the contents of `agent.env`.

3. If the MCP server started before `agent.env` existed, tell the user to reload the BotRelay MCP server, then continue.

4. Call `get_vault`.

5. Report only `id`, `name`, and `labels`.

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
3. Use the fields **in the tool that performs the action**: browser form fill, HTTP header, SDK client. Do not narrate the values.
4. If login needs a human (CAPTCHA, 2FA, magic link), stop and hand the desktop or a secure prompt back. Do not ask the user to paste the vault password into chat.

## Never do this

- Do not paste passwords, API keys, vault keys, agent tokens (`brt_live_…`), or full `get_secret` JSON into chat, logs, commits, screenshots, or PR text.
- Do not dump `list_secrets` plus `get_secret` for every label “just in case.”
- Do not send `BOTRELAY_VAULT_KEY` to the BotRelay API, a hosted MCP, or another bot.
- Do not fall back to `/home/box/botrelay/.env` or any shared credential file. This install's credentials are `~/.config/botrelay/agent.env` only.
- Do not invent a remote decrypt endpoint. There isn’t one.

## If tools fail

- Missing keys, or `botrelay_mcp` still has no `BOTRELAY_API_KEY` / `BOTRELAY_VAULT_KEY` after startup: `~/.config/botrelay/agent.env` is missing or incomplete. Ask the owner to install `botrelay-mcp` and `botrelay-cli` into `~/.venvs/botrelay` and run `botrelay agent configure`. That writes `agent.env` (mode 0600). Then reload the BotRelay MCP server. Do not ask them to paste keys into chat. The MCP package must load `agent.env` itself; Marketplace `mcp.json` does not source it.
- 401 from the API: wrong or rotated `BOTRELAY_API_KEY` for this vault. Run `botrelay agent configure` again for this agent.
- Decrypt errors: `BOTRELAY_VAULT_KEY` does not match this vault (or is not standard base64 of 32 bytes).
- Import / launch errors: install into this machine's venv
  (`python3 -m venv ~/.venvs/botrelay && ~/.venvs/botrelay/bin/pip install botrelay-mcp botrelay-cli`).
  Developers may instead install `packages/sdk-python` and `apps/mcp` in an editable checkout `.venv` and run
  `install-local.sh`. The plugin does not reimplement decryption.
