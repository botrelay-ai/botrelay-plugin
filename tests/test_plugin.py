from __future__ import annotations

import json
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
CURSOR_MANIFEST = PLUGIN / ".cursor-plugin" / "plugin.json"
MCP_JSON = PLUGIN / "mcp.json"
REQUIRED_FIELDS = ("BOTRELAY_API_URL", "BOTRELAY_API_KEY", "BOTRELAY_VAULT_KEY")
OPTIONAL_FIELDS = ("BOTRELAY_PYTHON",)
SETUP_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_cursor_manifest_declares_setup_fields() -> None:
    manifest = _load(CURSOR_MANIFEST)
    assert manifest["name"] == "botrelay"
    assert manifest["mcpServers"] == "./mcp.json"
    variables = manifest["variables"]
    assert variables["type"] == "object"
    for name in SETUP_FIELDS:
        assert name in variables["properties"]
        assert variables["properties"][name]["type"] == "string"
    assert set(variables["required"]) == set(REQUIRED_FIELDS)
    assert "BOTRELAY_PYTHON" not in variables["required"]
    assert variables["properties"]["BOTRELAY_API_URL"]["default"] == "https://api.botrelay.ai"
    assert "api key" in variables["properties"]["BOTRELAY_API_KEY"]["title"].lower()
    assert "vault key" in variables["properties"]["BOTRELAY_VAULT_KEY"]["title"].lower()
    assert "python" in variables["properties"]["BOTRELAY_PYTHON"]["title"].lower()
    assert "optional" in variables["properties"]["BOTRELAY_PYTHON"]["description"].lower()
    assert "author" in manifest and "name" in manifest["author"]
    extra = set(manifest["author"]) - {"name", "email"}
    assert not extra


def test_mcp_configs_wire_env_like_apps_mcp() -> None:
    cursor_mcp = _load(MCP_JSON)
    server = cursor_mcp["mcpServers"]["botrelay"]
    assert set(server) == {"command", "env"}
    assert server["command"] == "botrelay-mcp"
    for name in SETUP_FIELDS:
        assert server["env"][name] == "${" + name + "}"
    raw = json.dumps(server)
    for match in re.findall(r"\$\{([^}]+)\}", raw):
        assert match in SETUP_FIELDS
    assert "CURSOR_PLUGIN_ROOT" not in raw
    assert "launch.sh" not in raw


def test_mcp_command_is_console_script_not_a_workspace_path() -> None:
    """Marketplace cwd is the open workspace, not the plugin root.

    `./scripts/launch.sh` 404s when the workspace is a monorepo. Hosts such as
    Grok Bot leave ${CURSOR_PLUGIN_ROOT} unexpanded. The PyPI console script
    is on PATH and needs neither a plugin path nor a workspace path.
    """
    server = _load(MCP_JSON)["mcpServers"]["botrelay"]
    assert server["command"] == "botrelay-mcp"
    assert "/" not in server["command"]
    assert "\\" not in server["command"]
    assert "args" not in server
    assert "cwd" not in server
    raw = json.dumps(server)
    assert "launch.sh" not in raw
    assert "CURSOR_PLUGIN_ROOT" not in raw
    assert "GROK_PLUGIN_ROOT" not in raw
    assert "./scripts/" not in raw
    # launch.sh stays for local/dev; Marketplace mcp.json does not invoke it.
    assert (PLUGIN / "scripts" / "launch.sh").is_file()


def test_readme_documents_console_script_on_path() -> None:
    readme = (PLUGIN / "README.md").read_text()
    assert "pip install botrelay-mcp" in readme
    how = readme.split("## How it works", 1)[1].split("## ", 1)[0]
    assert "`botrelay-mcp`" in how
    assert "scripts/launch.sh" in how
    assert "./scripts/launch.sh" not in how
    assert "BOTRELAY_PYTHON" in readme
    assert "PATH" in readme


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
    rule = (PLUGIN / "rules" / "botrelay-secrets.mdc").read_text()
    assert "alwaysApply: true" in rule
    assert "BOTRELAY_VAULT_KEY" in rule


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
