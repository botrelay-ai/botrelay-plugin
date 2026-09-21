---
name: botrelay-secrets
description: Secure password vault for AI agents. Empower agents to do more while keeping your secrets safe.
---

# BotRelay secrets

This plugin wraps the **local** BotRelay MCP (`apps/mcp`). Ciphertext is fetched from the API and decrypted **in this process** with `BOTRELAY_VAULT_KEY`. The vault key must never be sent to `api.botrelay.ai` or any other host.

The install is bound to a single vault. Access secrets from this vault only for the current task. Don't hunt credentials for other bots or workflows.

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
- Do not fall back to `/home/box/botrelay/.env` or any shared credential file.
- Do not invent a remote decrypt endpoint. There isn’t one.

## If tools fail

- Missing keys / unsubstituted `${BOTRELAY_API_KEY}`: this account’s plugin setup fields are empty. Ask the owner to configure **this bot’s** URL, agent token, and vault key. Do not copy another bot’s values.
- 401 from the API: wrong or rotated `BOTRELAY_API_KEY` for this vault.
- Decrypt errors: `BOTRELAY_VAULT_KEY` does not match this vault (or is not standard base64 of 32 bytes).
- Import / launch errors: install `botrelay-mcp` on this machine
  (`python3 -m pip install botrelay-mcp`). Developers may instead install
  `packages/sdk-python` and `apps/mcp` in an editable checkout `.venv` and run
  `install-local.sh`. The plugin does not reimplement decryption.
