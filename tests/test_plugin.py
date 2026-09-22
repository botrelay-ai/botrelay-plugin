from __future__ import annotations

import json
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
CURSOR_MANIFEST = PLUGIN / ".cursor-plugin" / "plugin.json"
MCP_JSON = PLUGIN / "mcp.json"
SECRET_PLACEHOLDERS = ("${BOTRELAY_API_URL}", "${BOTRELAY_API_KEY}", "${BOTRELAY_VAULT_KEY}")


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_cursor_manifest_has_no_configure_variables() -> None:
    manifest = _load(CURSOR_MANIFEST)
    raw = CURSOR_MANIFEST.read_text()
    assert manifest["name"] == "botrelay"
    assert manifest["displayName"] == "BotRelay"
    assert manifest["mcpServers"] == "./mcp.json"
    assert manifest["skills"] == "./skills/"
    assert manifest["rules"] == "./rules/"
    assert manifest["commands"] == "./commands/"
    assert "variables" not in manifest
    assert "variables" not in raw
    for placeholder in SECRET_PLACEHOLDERS:
        assert placeholder not in raw
    assert "author" in manifest and "name" in manifest["author"]
    extra = set(manifest["author"]) - {"name", "email"}
    assert not extra


def test_mcp_configs_do_not_embed_secret_placeholders() -> None:
    cursor_mcp = _load(MCP_JSON)
    server = cursor_mcp["mcpServers"]["botrelay"]
    assert set(server) == {"command", "args"}
    assert "env" not in server
    assert server["command"] == "bash"
    assert server["args"] == ["${CURSOR_PLUGIN_ROOT}/scripts/launch.sh"]
    raw = MCP_JSON.read_text()
    for placeholder in SECRET_PLACEHOLDERS:
        assert placeholder not in raw
    assert "${BOTRELAY_PYTHON}" not in raw
    matches = re.findall(r"\$\{([A-Z][A-Z0-9_]*)\}", raw)
    assert matches == ["CURSOR_PLUGIN_ROOT"]
    assert "${PLUGIN_ROOT}" not in raw
    assert "GROK_PLUGIN_ROOT" not in raw
    assert "./scripts/" not in raw
    assert (PLUGIN / "scripts" / "launch.sh").is_file()


def test_mcp_command_uses_cursor_plugin_root_launch_script() -> None:
    """Shared MCP cwd is the workspace, so a relative launch path 404s.

    Cursor expands ${CURSOR_PLUGIN_ROOT} in mcp.json command and args. It does
    not expand the Agent Plugins ${PLUGIN_ROOT} variable. launch.sh then
    resolves BOTRELAY_PYTHON and ~/.venvs/botrelay when that env is missing.
    """
    raw = MCP_JSON.read_text()
    server = _load(MCP_JSON)["mcpServers"]["botrelay"]
    assert server["command"] == "bash"
    assert server["args"] == ["${CURSOR_PLUGIN_ROOT}/scripts/launch.sh"]
    assert "cwd" not in server
    assert "./scripts/launch.sh" not in raw
    assert "${PLUGIN_ROOT}" not in raw
    assert "CURSOR_PLUGIN_ROOT" in raw
    assert "-c" not in server["args"]


def test_readme_documents_agent_env_and_launch() -> None:
    readme = (PLUGIN / "README.md").read_text()
    assert "pip install botrelay-mcp botrelay-cli" in readme
    assert "botrelay agent configure" in readme
    assert ".config/botrelay/agent.env" in readme
    assert "0600" in readme
    assert "Try in Chat" in readme
    assert "/botrelay-login" in readme
    assert "Log into BotRelay and get the vault information." in readme
    assert "**Configure**" not in readme
    assert "Plugins → Configure" not in readme
    how = readme.split("## How it works", 1)[1].split("## ", 1)[0]
    assert "bash" in how.lower()
    assert "`botrelay-mcp`" in how
    assert "BOTRELAY_PYTHON" in how
    assert "agent.env" in how
    assert "${CURSOR_PLUGIN_ROOT}/scripts/launch.sh" in how
    assert "./scripts/launch.sh" not in how
    trouble = readme.split("## Troubleshooting", 1)[1]
    assert "./scripts/launch.sh" in trouble
    assert "${PLUGIN_ROOT}" in trouble
    assert "${CURSOR_PLUGIN_ROOT}" in trouble
    assert ".venvs/botrelay/bin/python3" in trouble
    assert "botrelay agent configure" in trouble
    assert "BOTRELAY_PYTHON" in readme
    assert "PATH" in readme
    assert "Shared MCP" in readme
    assert ".venvs/botrelay" in readme
    assert "botrelay-mcp: not found" in readme


def test_marketplace_points_at_plugin_root() -> None:
    market = _load(PLUGIN / ".cursor-plugin" / "marketplace.json")
    assert market["name"] == "botrelay"
    assert market["plugins"][0]["source"] == "."
    assert "marketplace/publish" not in json.dumps(market)


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
    assert "Plugins → Configure" not in skill
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
    assert "botrelay-mcp botrelay-cli" in command
    assert "get_vault" in command
    assert ".config/botrelay/agent.env" in command
    assert "0600" in command


def test_plugin_docs_and_defs_omit_stage_host() -> None:
    skip_suffixes = {".svg", ".pyc"}
    skip_dirs = {".pytest_cache", "__pycache__", "tests"}
    for path in PLUGIN.rglob("*"):
        if not path.is_file() or path.suffix in skip_suffixes:
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        text = path.read_text(errors="replace")
        assert "stage.botrelay.ai" not in text, path


def test_plugin_tree_has_no_real_tokens() -> None:
    skip_suffixes = {".svg", ".pyc"}
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
