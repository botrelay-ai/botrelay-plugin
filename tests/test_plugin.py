from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
CURSOR_MANIFEST = PLUGIN / ".cursor-plugin" / "plugin.json"
MCP_JSON = PLUGIN / "mcp.json"
PROD_ORIGIN = "https://api.botrelay.ai"
STAGE_ORIGIN = "https://stage.botrelay.ai"
HOSTED_MCP_URL = f"{PROD_ORIGIN}/mcp/"
MCP_URL_TEMPLATE = "${API_BASE_URL}/mcp/"


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_cursor_manifest_declares_api_base_url_and_api_key() -> None:
    manifest = _load(CURSOR_MANIFEST)
    raw = CURSOR_MANIFEST.read_text()
    assert manifest["name"] == "botrelay"
    assert manifest["displayName"] == "BotRelay"
    assert manifest["version"] == "0.3.2"
    assert manifest["logo"] == "assets/botrelay-logo-marketplace.png"
    logo = PLUGIN / manifest["logo"]
    assert logo.is_file()
    png = logo.read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert int.from_bytes(png[16:20], "big") == 256
    assert int.from_bytes(png[20:24], "big") == 256
    assert png[25] == 6  # RGBA
    assert manifest["mcpServers"] == "./mcp.json"
    assert manifest["skills"] == "./skills/"
    assert manifest["rules"] == "./rules/"
    assert manifest["commands"] == "./commands/"
    assert "author" in manifest and "name" in manifest["author"]
    extra = set(manifest["author"]) - {"name", "email"}
    assert not extra
    variables = manifest["variables"]
    assert variables["type"] == "object"
    assert set(variables["properties"]) == {"API_BASE_URL", "BOTRELAY_API_KEY"}
    assert variables["required"] == ["BOTRELAY_API_KEY"]
    base_url = variables["properties"]["API_BASE_URL"]
    assert base_url["type"] == "string"
    assert base_url["title"] == "API base URL"
    assert base_url["default"] == PROD_ORIGIN
    assert "enum" not in base_url
    assert base_url["description"] == (
        "Base URL of BotRelay API. Do not include /mcp/ in this value."
    )
    api_key = variables["properties"]["BOTRELAY_API_KEY"]
    assert api_key["type"] == "string"
    assert api_key["title"] == "API key"
    assert "enum" not in api_key
    assert "default" not in api_key
    assert "BOTRELAY_VAULT_KEY" not in raw
    assert "brt_live_" not in raw or "brt_live_…" in raw


def test_mcp_json_is_hosted_http_with_bearer_api_key_only() -> None:
    server = _load(MCP_JSON)["mcpServers"]["botrelay"]
    assert set(server) == {"type", "url", "headers"}
    assert server["type"] == "http"
    assert server["url"] == MCP_URL_TEMPLATE
    assert server["url"].endswith("/mcp/")
    assert PROD_ORIGIN not in server["url"]
    assert STAGE_ORIGIN not in server["url"]
    assert server["headers"] == {"Authorization": "Bearer ${BOTRELAY_API_KEY}"}
    raw = MCP_JSON.read_text()
    assert "command" not in server
    assert "args" not in server
    assert "env" not in server
    assert "BOTRELAY_VAULT_KEY" not in raw
    assert "botrelay_mcp" not in raw
    assert "botrelay-mcp" not in raw
    assert "${env:" not in raw
    assert "CURSOR_PLUGIN_ROOT" not in raw
    assert "${PLUGIN_ROOT}" not in raw
    assert "./scripts/" not in raw
    assert not (PLUGIN / ".mcp.json").exists()


def test_readme_documents_hosted_mcp_and_local_unlock() -> None:
    readme = (PLUGIN / "README.md").read_text()
    assert "uv tool install botrelay-cli" in readme
    assert "uv tool upgrade botrelay-cli" in readme
    assert "curl -LsSf https://astral.sh/uv/install.sh | sh" in readme
    assert "pip install -U botrelay-cli" in readme
    assert "If uv cannot be installed" in readme
    assert "pip install -U botrelay-mcp" not in readme
    assert "botrelay agent configure" in readme
    assert ".config/botrelay/agent.env" in readme
    assert "0600" in readme
    assert "/botrelay-login" in readme
    assert "Log into BotRelay and get the vault information." in readme
    assert "Plugins → Configure" in readme
    assert HOSTED_MCP_URL in readme
    assert MCP_URL_TEMPLATE in readme
    assert "API_BASE_URL" in readme
    assert STAGE_ORIGIN in readme
    assert "stage agent API key" in readme
    assert "private MCP config" not in readme
    assert "Bearer" in readme
    assert "${BOTRELAY_API_KEY}" in readme
    assert "botrelay agent decrypt" in readme
    assert "botrelay agent get" in readme
    assert "sealed" in readme.lower()
    assert "botrelay-mcp" in readme
    assert "deprecated" in readme.lower()
    how = readme.split("## How it works", 1)[1].split("## ", 1)[0]
    assert HOSTED_MCP_URL in how
    assert MCP_URL_TEMPLATE in how
    assert STAGE_ORIGIN in how
    assert "Authorization: Bearer" in how
    assert "agent.env" in how
    assert "does not start a command" in how
    assert '"type": "http"' in how
    assert "trailing slash" in how.lower()
    assert "vault key" in how.lower()
    assert "python -m botrelay_mcp" not in readme
    assert "daemon" not in readme.lower()
    assert "shim" not in readme.lower()
    assert "Unix domain socket" not in readme
    assert "named pipe" not in readme.lower()
    trouble = readme.split("## Troubleshooting", 1)[1]
    assert "Plugins → Configure" in trouble
    assert '"type": "http"' in trouble
    assert "https://api.botrelay.ai/mcp/" in trouble
    assert MCP_URL_TEMPLATE in trouble
    assert "API_BASE_URL" in trouble
    assert "trailing slash" in trouble.lower()
    assert "get_secret" in trouble
    assert "botrelay agent decrypt" in trouble
    assert "botrelay-mcp" in trouble
    assert "Works in Cursor, fails in a Grok agent" in trouble
    assert "[Grok Bot](#grok-bot)" in trouble
    assert "agent token" not in readme.lower()
    assert "API key (`brt_live_…`)" in readme
    grok = readme.split("## Grok Bot", 1)[1].split("## ", 1)[0]
    assert "shared virtual machine" in grok
    assert "own desktop and browser" in grok
    assert "~/.venvs/botrelay" in grok
    assert "~/.config/botrelay/agent.env" in grok
    assert "uv tool install botrelay-cli" in grok
    assert "Do not reinstall" in grok
    assert "import botrelay_mcp" not in grok
    assert "pip install -U botrelay-cli" not in grok
    assert "0600" in grok
    assert "do not paste the api key or vault key into chat" in grok.lower()
    assert "hand the desktop to the user" in grok.lower()
    assert "host secure secret inputs" in grok.lower()
    assert "--api-url" in grok and "--api-key" in grok and "--vault-key" in grok
    assert "https://api.botrelay.ai" in grok
    assert "do not use browser form-fill tools to write `agent.env`" in grok.lower()
    assert "every agent on that Grok account" in grok
    assert "do not each install or configure" in grok
    assert "skip" in grok.lower() and "get_vault" in grok
    assert "separate machine" in grok
    assert "second local `agent.env`" in grok
    assert "does not create `agent.env` on the Grok VM" in grok
    assert "does not create `agent.env` on the Mac" in grok
    assert "new device" in grok
    assert "Plugins → Configure" in grok
    assert "[Grok Bot](#grok-bot)" in readme.split("## Grok Bot", 1)[0]
    configure = readme.split("## Install", 1)[1].split("## How it works", 1)[0]
    assert STAGE_ORIGIN in configure
    assert "API_BASE_URL" in configure


def test_skill_and_login_teach_hosted_mcp_and_local_decrypt() -> None:
    skill = (PLUGIN / "skills" / "botrelay-secrets" / "SKILL.md").read_text()
    command = (PLUGIN / "commands" / "botrelay-login.md").read_text()
    rule = (PLUGIN / "rules" / "botrelay-secrets.mdc").read_text()
    for path, text in (
        ("skill", skill),
        ("command", command),
    ):
        lowered = text.lower()
        assert "agent token" not in lowered, path
        assert "import botrelay_mcp" not in text, path
        assert "botrelay-mcp" in text, path
        assert ".config/botrelay/agent.env" in text, path
        assert "uv tool install botrelay-cli" in text, path
        assert "uv tool upgrade botrelay-cli" in text, path
        assert "command -v botrelay" in text, path
        assert "~/.local/bin" in text, path
        assert "uv tool update-shell" in text, path
        assert "curl -LsSf https://astral.sh/uv/install.sh | sh" in text, path
        assert 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"' in text, path
        assert "If uv cannot be installed" in text, path
        assert "python3 -m venv ~/.venvs/botrelay" in text, path
        assert "Do not reinstall" in text, path
        assert "pip install -U botrelay-mcp" not in text, path
        assert HOSTED_MCP_URL in text, path
        assert "API key (`brt_live_…`)" in text, path
        assert "Vault key" in text or "vault key" in text, path
        assert "--api-url" in text and "--api-key" in text and "--vault-key" in text, path
        assert "hand the desktop to the user" in lowered, path
        assert "host secure secret inputs" in lowered, path
        assert "do not use browser form-fill tools to write `agent.env`" in lowered, path
        assert "get_vault" in text, path
        assert "get_secret" in text, path
        assert "botrelay agent decrypt" in text, path
        assert "botrelay agent get" in text, path
        assert "Plugins → Configure" in text, path
        assert "sealed" in lowered, path
        assert "daemon" not in lowered, path
        assert "shim" not in lowered, path
        assert "shared virtual machine" in lowered or "share one virtual machine" in lowered, path
        assert "own desktop and browser" in lowered, path
        assert "does not create `agent.env` on the Grok VM" in text, path
        assert "does not create `agent.env` on the Mac" in text, path
        assert "skip install and configure" in lowered, path
        assert "fourth credential" in lowered, path
        assert "wins over the process environment" in lowered, path
    assert "agent token" not in rule.lower()
    assert "skip install and configure" in rule.lower()
    assert "API key (`brt_live_…`)" in rule
    assert "does not create `agent.env` on the Grok VM" in rule
    assert "browser form-fill tools to write `agent.env`" in rule.lower()
    assert "BOTRELAY_VAULT_KEY" in rule
    assert HOSTED_MCP_URL in rule
    assert "botrelay agent decrypt" in rule
    assert "sealed" in rule.lower()
    assert "daemon" not in rule.lower()


def test_marketplace_points_at_plugin_root() -> None:
    market = _load(PLUGIN / ".cursor-plugin" / "marketplace.json")
    assert market["name"] == "botrelay"
    assert market["plugins"][0]["source"] == "."
    blob = json.dumps(market)
    assert "marketplace/publish" not in blob
    assert "botrelay-mcp" not in blob
    assert "local MCP" not in blob
    assert "sealed" in blob.lower()


def test_skill_enters_web_passwords_through_the_clipboard() -> None:
    skill = (PLUGIN / "skills" / "botrelay-secrets" / "SKILL.md").read_text()
    section = skill.split("## Entering a password into a web page", 1)[1].split("## ", 1)[0]
    how = skill.split("## How to use a secret", 1)[1].split("## ", 1)[0]
    assert "Entering a password into a web page" in how
    assert "browser form fill" not in how.lower()
    assert "do not use browser form-fill tools to write `agent.env`" in how.lower()
    assert "xclip -selection clipboard" in section
    assert "-loops" in section
    assert "wl-copy" in section
    assert "--paste-once" in section
    assert "pbcopy" in section
    assert "| clip" in section
    assert "Set-Clipboard" in section
    assert "Ctrl+V" in section
    assert "Cmd+V" in section
    assert "address bar" in section.lower()
    assert "masked" in section.lower()
    assert "shared VM" in section
    assert "jq -r" in section
    assert "~/.venvs/botrelay" not in section
    assert "uv run --no-project --quiet python" in section
    programs = re.findall(r'uv run --no-project --quiet python -c "([^"]+)"', section)
    assert len(programs) == 5
    assert len(set(programs)) == 1
    program = programs[0]
    payload = json.dumps(
        {
            "username": "octocat",
            "password": "Pike-place ",
            "label": "github",
            "secret_type": "password",
        },
        indent=2,
    ) + "\n"
    runners = [["python3", "-c", program]]
    uv = shutil.which("uv")
    if uv:
        runners.append([uv, "run", "--no-project", "--quiet", "python", "-c", program])
    for argv in runners:
        proc = subprocess.run(
            argv,
            input=payload.encode(),
            capture_output=True,
            check=False,
        )
        assert proc.returncode == 0, argv
        assert proc.stdout == "Pike-place ".encode(), argv
        assert proc.stderr.decode() == "octocat\n11\n", argv
        refused = subprocess.run(
            argv,
            input=b'{"key":"sk-test","secret_type":"api_key"}\n',
            capture_output=True,
            check=False,
        )
        assert refused.returncode != 0, argv
        assert refused.stdout == b"", argv
        assert b"sk-test" not in refused.stderr, argv


def test_skill_and_rule_frontmatter() -> None:
    skill = (PLUGIN / "skills" / "botrelay-secrets" / "SKILL.md").read_text()
    assert skill.startswith("---\n")
    assert "name: botrelay-secrets" in skill
    assert "list_secrets" in skill
    assert "get_secret" in skill
    assert "never paste" in skill.lower() or "do not paste" in skill.lower()
    assert "chat" in skill.lower()
    assert "botrelay agent configure" in skill
    assert ".config/botrelay/agent.env" in skill
    assert "get_vault" in skill
    rule = (PLUGIN / "rules" / "botrelay-secrets.mdc").read_text()
    assert "alwaysApply: true" in rule
    assert "BOTRELAY_VAULT_KEY" in rule
    assert "agent.env" in rule
    assert "botrelay agent configure" in rule
    command = (PLUGIN / "commands" / "botrelay-login.md").read_text()
    assert command.startswith("---\n")
    assert "name: botrelay-login" in command
    assert "Log into BotRelay and get the vault information." in command
    assert "botrelay agent configure" in command
    assert "botrelay-cli" in command
    assert "get_vault" in command
    assert ".config/botrelay/agent.env" in command
    assert "0600" in command
    assert "botrelay agent decrypt" in command


def test_stage_host_is_a_documented_origin_not_hardcoded_in_mcp() -> None:
    skip_suffixes = {".svg", ".png", ".pyc"}
    skip_dirs = {".pytest_cache", "__pycache__", "tests"}
    hits: list[Path] = []
    for path in PLUGIN.rglob("*"):
        if not path.is_file() or path.suffix in skip_suffixes:
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        text = path.read_text(errors="replace")
        if "stage.botrelay.ai" in text:
            hits.append(path)
    assert hits == [PLUGIN / "README.md"]
    mcp = MCP_JSON.read_text()
    assert STAGE_ORIGIN not in mcp
    assert MCP_URL_TEMPLATE in mcp


def test_plugin_tree_has_no_real_tokens() -> None:
    skip_suffixes = {".svg", ".png", ".pyc"}
    skip_dirs = {".pytest_cache", "__pycache__", "tests"}
    for path in PLUGIN.rglob("*"):
        if not path.is_file() or path.suffix in skip_suffixes:
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        text = path.read_text(errors="replace")
        if "brt_live_" in text:
            assert "brt_live_…" in text or "brt_live_..." in text, path
        assert "BOTRELAY_VAULT_KEY=AAAA" not in text
        assert "/home/box/botrelay/.env" not in text or "Do not" in text or "do not" in text or "Never" in text
