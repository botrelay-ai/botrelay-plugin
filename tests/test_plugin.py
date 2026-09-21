from __future__ import annotations

import json
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
REPO = PLUGIN.parents[1]
CURSOR_MANIFEST = PLUGIN / ".cursor-plugin" / "plugin.json"
GROK_MANIFEST = PLUGIN / ".grok-plugin" / "plugin.json"
MCP_JSON = PLUGIN / "mcp.json"
DOT_MCP_JSON = PLUGIN / ".mcp.json"
REQUIRED_FIELDS = ("BOTRELAY_API_URL", "BOTRELAY_API_KEY", "BOTRELAY_VAULT_KEY")
OPTIONAL_FIELDS = ("BOTRELAY_PYTHON",)
SETUP_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS
PLUGIN_ROOT_VARS = frozenset({"CURSOR_PLUGIN_ROOT", "GROK_PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT"})
LAUNCHER_NAME = "scripts/launch.sh"


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


def test_grok_manifest_pins_dot_mcp() -> None:
    manifest = _load(GROK_MANIFEST)
    assert manifest["name"] == "botrelay"
    assert manifest["mcpServers"] == "./.mcp.json"
    assert "variables" not in manifest  # Cursor-only schema; Grok uses the same env via .mcp.json


def _configured_launcher(server: dict) -> str:
    parts = [server.get("command") or "", *(server.get("args") or [])]
    for part in parts:
        if "launch.sh" in part:
            return part
    raise AssertionError(f"no launch.sh in command/args: {parts}")


def test_mcp_configs_wire_env_like_apps_mcp() -> None:
    cursor_mcp = _load(MCP_JSON)
    grok_mcp = _load(DOT_MCP_JSON)
    assert cursor_mcp == grok_mcp
    server = cursor_mcp["mcpServers"]["botrelay"]
    assert server["command"] == "bash"
    assert (PLUGIN / "scripts" / "launch.sh").is_file()
    for name in SETUP_FIELDS:
        assert server["env"][name] == "${" + name + "}"
    raw = json.dumps(server)
    for match in re.findall(r"\$\{([^}]+)\}", raw):
        assert match in SETUP_FIELDS or match in PLUGIN_ROOT_VARS


def test_mcp_launcher_is_plugin_rooted_not_repo_cwd() -> None:
    """Team Marketplace spawns with cwd = monorepo root, not plugins/botrelay.

    `./scripts/launch.sh` becomes <checkout>/scripts/launch.sh and 404s.
    """
    assert not (REPO / LAUNCHER_NAME).exists()
    assert (PLUGIN / LAUNCHER_NAME).is_file()
    for path in (MCP_JSON, DOT_MCP_JSON):
        server = _load(path)["mcpServers"]["botrelay"]
        configured = _configured_launcher(server)
        assert not configured.startswith("./"), configured
        assert "./scripts/launch.sh" not in configured
        assert "${CURSOR_PLUGIN_ROOT}/" in configured or "${GROK_PLUGIN_ROOT}/" in configured
        _, sep, rel = configured.partition("}/")
        assert sep, configured
        assert rel == LAUNCHER_NAME
        assert (PLUGIN / rel).is_file()
        assert not (REPO / rel).exists()
        cwd = server.get("cwd")
        assert cwd in {f"${{{name}}}" for name in PLUGIN_ROOT_VARS}


def test_private_marketplaces_point_at_plugin() -> None:
    cursor_market = _load(REPO / ".cursor-plugin" / "marketplace.json")
    grok_market = _load(REPO / ".grok-plugin" / "marketplace.json")
    assert cursor_market["name"] == "botrelay-private"
    assert cursor_market["plugins"][0]["source"] == "plugins/botrelay"
    assert grok_market["plugins"][0]["source"]["path"] == "./plugins/botrelay"
    for blob in (json.dumps(cursor_market), json.dumps(grok_market)):
        assert "marketplace/publish" not in blob


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
