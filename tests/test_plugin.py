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
    py_desc = variables["properties"]["BOTRELAY_PYTHON"]["description"].lower()
    assert "optional" in py_desc
    assert "marketplace" in py_desc
    assert "path" in py_desc
    assert "author" in manifest and "name" in manifest["author"]
    extra = set(manifest["author"]) - {"name", "email"}
    assert not extra


def test_mcp_configs_wire_env_like_apps_mcp() -> None:
    cursor_mcp = _load(MCP_JSON)
    server = cursor_mcp["mcpServers"]["botrelay"]
    assert set(server) == {"command", "args", "env"}
    assert server["command"] == "bash"
    assert server["args"][0] == "-c"
    assert server["args"][2] == "botrelay"
    assert server["args"][3] == "${BOTRELAY_PYTHON}"
    assert len(server["args"]) == 4
    for name in SETUP_FIELDS:
        assert server["env"][name] == "${" + name + "}"
    raw = json.dumps(server)
    for match in re.findall(r"\$\{([A-Z][A-Z0-9_]*)\}", raw):
        assert match in SETUP_FIELDS
    assert "CURSOR_PLUGIN_ROOT" not in raw
    assert "launch.sh" not in raw


def test_mcp_command_resolves_python_without_a_path_entry() -> None:
    """Shared MCP cwd is the workspace, not the plugin root.

    Profile-scoped launch receives Configure env. The Shared MCP spawn often
    does not, and its GUI PATH has no botrelay-mcp, so a bare exec fails and
    the status goes red. ${CURSOR_PLUGIN_ROOT} is left unexpanded on some
    hosts, so the resolver stays inside bash -c and probes ~/.venvs/botrelay.
    BOTRELAY_PYTHON is a dedicated argv (not only a nested shell variable) so
    Cursor can expand it in command/args without rewriting the script.
    """
    server = _load(MCP_JSON)["mcpServers"]["botrelay"]
    assert server["command"] == "bash"
    assert "/" not in server["command"]
    assert "\\" not in server["command"]
    assert server["args"][0] == "-c"
    script = server["args"][1]
    assert "${BOTRELAY_PYTHON}" not in script
    assert "printenv BOTRELAY_PYTHON" in script
    assert "-m botrelay_mcp" in script
    assert ".venvs/botrelay/bin/python3" in script
    assert ".venvs/botrelay/bin/python" in script
    assert "command -v botrelay-mcp" in script
    assert "else exec botrelay-mcp" not in script
    assert "import botrelay_mcp" in script
    assert "*'${'*" in script
    assert "cwd" not in server
    raw = json.dumps(server)
    assert "launch.sh" not in raw
    assert "CURSOR_PLUGIN_ROOT" not in raw
    assert "GROK_PLUGIN_ROOT" not in raw
    assert "./scripts/" not in raw
    # launch.sh stays for local/dev; Marketplace mcp.json does not invoke it.
    assert (PLUGIN / "scripts" / "launch.sh").is_file()


def test_readme_documents_bash_launch_and_botrelay_python() -> None:
    readme = (PLUGIN / "README.md").read_text()
    assert "pip install botrelay-mcp" in readme
    how = readme.split("## How it works", 1)[1].split("## ", 1)[0]
    assert "bash" in how.lower()
    assert "`botrelay-mcp`" in how
    assert "BOTRELAY_PYTHON" in how
    assert "scripts/launch.sh" in how
    assert "./scripts/launch.sh" not in how
    assert "BOTRELAY_PYTHON" in readme
    assert "PATH" in readme
    assert "Shared MCP" in readme
    assert ".venvs/botrelay" in readme
    assert "botrelay-mcp: not found" in readme
    # Configure copy: optional python path, PATH is only a fallback.
    configure = readme.split("**Configure**", 1)[1].split("4.", 1)[0]
    assert "BOTRELAY_PYTHON" in configure
    assert "PATH" in configure
    assert ".venvs/botrelay" in configure


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
