---
name: botrelay-secrets
description: Secure password vault for AI agents. Use when logging into BotRelay, loading vault information, calling get_vault, list_secrets, or get_secret, decrypting a sealed secret with botrelay agent decrypt, entering a decrypted password into a web page, or doing one-time setup of botrelay (uv) and agent.env on the shared Grok VM. Never paste API or vault keys into chat.
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

`botrelay` and `~/.config/botrelay/agent.env` belong to the machine that runs the CLI. `uv tool install` puts `botrelay` in `~/.local/bin`. An existing `~/.venvs/botrelay/bin/botrelay` on that machine is the same CLI.

Grok Bot agents share one virtual machine. Each agent has its own desktop and browser on that VM. They share one filesystem, so one CLI and one `agent.env` serve every agent on that Grok account. They do not each install or configure. If `~/.venvs/botrelay/bin/botrelay` already works there, keep using it. Do not reinstall.

Cursor on a Mac is a separate machine. `botrelay agent configure` in Cursor on a Mac does not create `agent.env` on the Grok VM. Configuring the Grok VM does not create `agent.env` on the Mac. The same API key and vault key are fine on both machines. Each machine gets its own local `agent.env`.

Hosted MCP auth is per Cursor or Grok account: set `BOTRELAY_API_KEY` under **Plugins → Configure** on each account that should call hosted MCP. The key is sent to whatever `API_BASE_URL` is configured (default `https://api.botrelay.ai`, so `https://api.botrelay.ai/mcp/`). Those settings are not `agent.env`. The CLI origin is `BOTRELAY_API_URL` in `agent.env` and should match `API_BASE_URL` when both talk to the same environment.

## Log into BotRelay and get the vault information

When the user asks to log into BotRelay, get vault information, or runs `/botrelay-login`, do this on the machine where this agent is running. On a Grok agent that machine is the shared VM, not the user's Mac. Prove login with hosted `get_vault`, not by importing `botrelay_mcp`.

1. Check for `botrelay` on `PATH` and the credential file. Do not print `agent.env`.

   ```bash
   command -v botrelay >/dev/null 2>&1 && echo cli-present || echo cli-missing
   botrelay --version >/dev/null 2>&1 && echo version-ok || echo version-missing
   botrelay agent decrypt --help >/dev/null 2>&1 && echo decrypt-ok || echo decrypt-missing
   test -x ~/.venvs/botrelay/bin/botrelay && echo legacy-venv-present || echo legacy-venv-missing
   test -f ~/.config/botrelay/agent.env && echo agent-env-present || echo agent-env-missing
   ```

   uv puts `botrelay` in `~/.local/bin`. If `command -v botrelay` fails after install, run `uv tool update-shell` and put that directory on `PATH` (`export PATH="$HOME/.local/bin:$PATH"`). On Windows, `where.exe botrelay` or `botrelay --version` is the same check. The tool directory is `%USERPROFILE%\.local\bin`.

   If `botrelay` is not on `PATH` but `~/.venvs/botrelay/bin/botrelay agent decrypt --help` succeeds, keep that binary. Call `~/.venvs/botrelay/bin/botrelay` anywhere this skill says `botrelay`. Do not reinstall.

2. If `botrelay` is missing and the legacy venv binary is not working, install `botrelay-cli` with uv. Do not install `botrelay-mcp`. uv brings its own Python. The machine does not need Python preinstalled.

   If `uv` itself is missing, install it first.

   macOS and Linux:

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source "$HOME/.local/bin/env"
   ```

   Windows PowerShell:

   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

   Then install the CLI and make sure the current shell can see it:

   ```bash
   uv tool install botrelay-cli
   uv tool update-shell
   export PATH="$HOME/.local/bin:$PATH"
   ```

   Upgrade an existing uv install with `uv tool upgrade botrelay-cli`.

   If uv cannot be installed, the fallback needs a system Python. Prefer uv. Do not use this fallback to replace a working legacy venv:

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
   botrelay agent configure
   ```

   On a TTY the CLI prompts for `API URL [https://api.botrelay.ai]:`, then a hidden `API key:`, then a hidden `Vault key:`. On a Grok agent, run that command in a terminal on the agent's desktop and hand the desktop to the user so they type the hidden prompts. Do not ask them to paste the API key or vault key into chat. Do not read `agent.env` or repeat the values.

   When there is no TTY, host secure secret inputs for those three labels, then run non-interactive configure with flags. Do not echo the values in chat, logs, or tool arguments:

   ```bash
   botrelay agent configure \
     --api-url "$BOTRELAY_API_URL" \
     --api-key "$BOTRELAY_API_KEY" \
     --vault-key "$BOTRELAY_VAULT_KEY"
   ```

   `--yes` overwrites an existing file without a confirmation prompt. Do not use browser form-fill tools to write `agent.env`. After the file exists, CLI commands use it instead of the process environment. Re-run configure to change keys. Do not expect exported variables to override `agent.env`.

5. If hosted MCP is not connected, tell the user to set plugin variable `BOTRELAY_API_KEY` under **Plugins → Configure** (agent API key only) and reload the BotRelay MCP server. Do not ask them to paste the key into chat. Do not enter the vault key. The host then calls `${API_BASE_URL}/mcp/` (default `https://api.botrelay.ai/mcp/`) with `Authorization: Bearer`. Use an agent API key issued for that `API_BASE_URL`.

6. Call `get_vault`. Optionally confirm the same metadata with `botrelay agent vault`. Do not call `botrelay agent get` during login.

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
botrelay agent get <label>
```

**MCP path** — when you already called `get_secret` and hold the sealed JSON:

```bash
umask 077
sealed="$(mktemp)"
# Write the get_secret JSON to "$sealed". Do not print it.
botrelay agent decrypt "$sealed"
rm -f "$sealed"
```

Stdin works the same way: `botrelay agent decrypt < "$sealed"`. Decrypt output is the typed secret (`Password`, `ApiKey`, or `Contact`), the same shape a local get used to return.

Then:

1. Call `list_secrets` (or `get_vault`) and pick a `label`.
2. Run `botrelay agent get <label>`, or call `get_secret` and pass that sealed JSON to `botrelay agent decrypt`. When the secret is a password for a web page, run that command only as the clipboard pipe in **Entering a password into a web page**, so the password is not printed.
3. Use the fields **in the tool that performs the action**. For a password on a web page, follow **Entering a password into a web page**: the clipboard is how that password gets into the form. An HTTP header or SDK client takes the field inside that tool. Do not narrate the values. Do not use browser form-fill tools to write `agent.env`.
4. Delete any sealed temp file. Do not commit it.
5. If login needs a human (CAPTCHA, 2FA, magic link), stop and hand the desktop or a secure prompt back. Do not ask the user to paste the vault password into chat.

## Entering a password into a web page

The clipboard is how a decrypted password gets into a web page. Click the masked password field, paste once, check the masked length, then clear the clipboard. Do not look for a form-fill tool. Do not type the password. Do not echo it, and do not put it in a command argument, chat, log, screenshot, or tool-call text.

`botrelay agent get <label>` writes indented JSON to stdout and a trailing newline (`botrelay-cli` 0.1.2, `json.dump(..., indent=2)`). A password secret has `username`, `password`, `label`, and `secret_type` set to `password`. Do not run that command unless its stdout is the pipe below. Parse the JSON in that pipe and write only the `password` bytes to the clipboard tool, with no extra newline (`jq -r` adds one). Do not cut the field out with the shell. Stderr prints the username, then the character count. Use those two lines. The password itself stays on the pipe. If the process exits with `not a password secret`, stop.

Do not limit how many times the clipboard can be read. A clipboard manager reads it too. Do not pass `-loops` to `xclip` or `--paste-once` to `wl-copy`.

Click the password field first and confirm the characters are masked. Never paste into the address bar, a search box, or any field that shows text in plain view. If `xclip` or `wl-copy` is missing, install it. Do not type the password instead.

The extractor is `uv run --no-project --quiet python`. That uses uv's Python, not the BotRelay venv and not a preinstalled `python3`. `--quiet` keeps uv's download logs off stderr, so stderr stays the username, then the character count. If this machine has no `uv` because you kept the legacy venv CLI, run the same program with `python3` in place of `uv run --no-project --quiet python`.

Linux X11:

```bash
botrelay agent get <label> | uv run --no-project --quiet python -c "import json,sys; doc=json.load(sys.stdin); pw=doc['password'] if doc.get('secret_type')=='password' else sys.exit('not a password secret'); sys.stderr.write(doc.get('username','')+'\n'+str(len(pw))+'\n'); sys.stdout.buffer.write(pw.encode())" | xclip -selection clipboard
```

Wayland:

```bash
botrelay agent get <label> | uv run --no-project --quiet python -c "import json,sys; doc=json.load(sys.stdin); pw=doc['password'] if doc.get('secret_type')=='password' else sys.exit('not a password secret'); sys.stderr.write(doc.get('username','')+'\n'+str(len(pw))+'\n'); sys.stdout.buffer.write(pw.encode())" | wl-copy
```

macOS:

```bash
botrelay agent get <label> | uv run --no-project --quiet python -c "import json,sys; doc=json.load(sys.stdin); pw=doc['password'] if doc.get('secret_type')=='password' else sys.exit('not a password secret'); sys.stderr.write(doc.get('username','')+'\n'+str(len(pw))+'\n'); sys.stdout.buffer.write(pw.encode())" | pbcopy
```

Windows Command Prompt, last stage `clip`:

```bat
botrelay agent get <label> | uv run --no-project --quiet python -c "import json,sys; doc=json.load(sys.stdin); pw=doc['password'] if doc.get('secret_type')=='password' else sys.exit('not a password secret'); sys.stderr.write(doc.get('username','')+'\n'+str(len(pw))+'\n'); sys.stdout.buffer.write(pw.encode())" | clip
```

Windows PowerShell, last stage `Set-Clipboard`:

```powershell
botrelay agent get <label> | uv run --no-project --quiet python -c "import json,sys; doc=json.load(sys.stdin); pw=doc['password'] if doc.get('secret_type')=='password' else sys.exit('not a password secret'); sys.stderr.write(doc.get('username','')+'\n'+str(len(pw))+'\n'); sys.stdout.buffer.write(pw.encode())" | Set-Clipboard
```

Paste once: Ctrl+V on Linux and Windows, Cmd+V on macOS.

Before submitting, count the masked characters in the password field. The count must match the number on stderr. If the field is empty or the count is wrong, clear the field and paste again. Do not submit until it matches.

Clear the clipboard as soon as the count matches. Also clear it if you stop, the login fails, or you abort:

- Linux X11: `printf '' | xclip -selection clipboard`
- Wayland: `wl-copy --clear`
- macOS: `pbcopy < /dev/null`
- Windows Command Prompt: `clip < NUL`
- Windows PowerShell: `Set-Clipboard -Value ''`

On a shared VM every agent and process can read the clipboard. Keep the password there only for the paste.

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
- CLI missing keys or decrypt errors: `~/.config/botrelay/agent.env` is missing, invalid, or the vault key does not match this vault (or is not standard base64 of 32 bytes). On a Grok agent, a file on the user's Mac does not count. If `botrelay` is missing, install with `uv tool install botrelay-cli`, then run `botrelay agent configure` (TTY and desktop handoff, or secure secret inputs plus `--api-url`, `--api-key`, and `--vault-key`).
- `botrelay agent decrypt` is not a subcommand: `uv tool upgrade botrelay-cli`. Do not install `botrelay-mcp` to replace it. A working `~/.venvs/botrelay/bin/botrelay` does not need a reinstall.
