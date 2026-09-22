from __future__ import annotations

import json
import re
import stat
import subprocess
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
    assert manifest["version"] == "0.1.1"
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
    assert server["args"][0] == "-lc"
    script = server["args"][1]
    assert "-m botrelay_mcp" in script
    assert "$HOME/.venvs/botrelay/bin/python3" in script
    raw = MCP_JSON.read_text()
    for placeholder in SECRET_PLACEHOLDERS:
        assert placeholder not in raw
    # Shell uses $BOTRELAY_PYTHON. A ${BOTRELAY_PYTHON} token would be a host
    # plugin variable; Grok would leave it unsubstituted.
    assert "${BOTRELAY_PYTHON}" not in raw
    matches = re.findall(r"\$\{([A-Z][A-Z0-9_]*)\}", raw)
    assert matches == []
    assert "CURSOR_PLUGIN_ROOT" not in raw
    assert "${PLUGIN_ROOT}" not in raw
    assert "GROK_PLUGIN_ROOT" not in raw
    assert "./scripts/" not in raw
    assert ".cursor/plugins" not in raw
    assert "source " not in script
    assert "agent.env" in script
    assert (PLUGIN / "scripts" / "launch.sh").is_file()
    assert not (PLUGIN / ".mcp.json").exists()


def test_mcp_command_uses_home_venv_entrypoint() -> None:
    """Grok and Cursor share one mcp.json. Neither host expands a plugin root.

    Shared MCP cwd is the workspace, so a relative launch path 404s. The
    command is bash -lc and execs python -m botrelay_mcp from the home venv
    (or BOTRELAY_PYTHON). botrelay_mcp loads agent.env; this shell does not.
    """
    raw = MCP_JSON.read_text()
    server = _load(MCP_JSON)["mcpServers"]["botrelay"]
    script = server["args"][1]
    assert server["command"] == "bash"
    assert server["args"][0] == "-lc"
    assert "cwd" not in server
    assert "./scripts/launch.sh" not in raw
    assert "${PLUGIN_ROOT}" not in raw
    assert "CURSOR_PLUGIN_ROOT" not in raw
    assert "$BOTRELAY_PYTHON" in script
    assert "$HOME/.venvs/botrelay/bin/python3" in script
    assert "$HOME/.venvs/botrelay/bin/python" in script
    assert "$HOME/.venvs/botrelay/Scripts/python.exe" in script
    assert "exec " in script
    assert "-m botrelay_mcp" in script
    assert "source " not in script
    assert ". \"$HOME" not in script
    assert "agent.env" in script


def _mcp_command() -> list[str]:
    server = _load(MCP_JSON)["mcpServers"]["botrelay"]
    return [server["command"], *server["args"]]


def _probe(path: Path, marker: str, code: int, *, import_ok: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    import_exit = "0" if import_ok else "1"
    path.write_text(
        "#!/bin/sh\n"
        'if [ "${1:-}" = "-c" ]; then\n'
        f"  exit {import_exit}\n"
        "fi\n"
        'if [ "$1" = "-m" ] && [ "$2" = "botrelay_mcp" ]; then\n'
        f"  echo {marker} >&2\n"
        f"  exit {code}\n"
        "fi\n"
        "echo UNEXPECTED >&2\n"
        "exit 2\n"
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _run_mcp(
    tmp_path: Path,
    home: Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin"}
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        _mcp_command(),
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )


def test_mcp_json_execs_home_python3(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _probe(home / ".venvs" / "botrelay" / "bin" / "python3", "MARKER_PY3", 44)
    _probe(home / ".venvs" / "botrelay" / "bin" / "python", "MARKER_BIN", 45)
    _probe(home / ".venvs" / "botrelay" / "Scripts" / "python.exe", "MARKER_WIN", 46)
    proc = _run_mcp(tmp_path, home)
    assert proc.returncode == 44, proc.stderr
    assert proc.stdout == ""
    assert "MARKER_PY3" in proc.stderr
    assert "MARKER_BIN" not in proc.stderr
    assert "MARKER_WIN" not in proc.stderr


def test_mcp_json_prefers_botrelay_python(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _probe(home / ".venvs" / "botrelay" / "bin" / "python3", "MARKER_PY3", 44)
    custom = tmp_path / "custom" / "python3"
    _probe(custom, "MARKER_OVERRIDE", 41)
    proc = _run_mcp(tmp_path, home, {"BOTRELAY_PYTHON": str(custom)})
    assert proc.returncode == 41, proc.stderr
    assert "MARKER_OVERRIDE" in proc.stderr
    assert "MARKER_PY3" not in proc.stderr


def test_mcp_json_expands_tilde_botrelay_python(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _probe(home / "py" / "python3", "USED_TILDE", 48)
    proc = _run_mcp(tmp_path, home, {"BOTRELAY_PYTHON": "~/py/python3"})
    assert proc.returncode == 48, proc.stderr
    assert "USED_TILDE" in proc.stderr


def test_mcp_json_skips_unsubstituted_botrelay_python(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _probe(home / ".venvs" / "botrelay" / "bin" / "python3", "MARKER_PY3", 44)
    proc = _run_mcp(tmp_path, home, {"BOTRELAY_PYTHON": "${BOTRELAY_PYTHON}"})
    assert proc.returncode == 44, proc.stderr
    assert "MARKER_PY3" in proc.stderr


def test_mcp_json_falls_back_when_python3_cannot_import(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _probe(
        home / ".venvs" / "botrelay" / "bin" / "python3",
        "MARKER_PY3",
        44,
        import_ok=False,
    )
    _probe(home / ".venvs" / "botrelay" / "bin" / "python", "MARKER_BIN", 45)
    proc = _run_mcp(tmp_path, home)
    assert proc.returncode == 45, proc.stderr
    assert "MARKER_BIN" in proc.stderr
    assert "MARKER_PY3" not in proc.stderr


def test_mcp_json_uses_windows_python_exe(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _probe(home / ".venvs" / "botrelay" / "Scripts" / "python.exe", "MARKER_WIN", 46)
    proc = _run_mcp(tmp_path, home)
    assert proc.returncode == 46, proc.stderr
    assert "MARKER_WIN" in proc.stderr


def test_mcp_json_does_not_load_agent_env(tmp_path: Path) -> None:
    home = tmp_path / "home"
    py = home / ".venvs" / "botrelay" / "bin" / "python3"
    py.parent.mkdir(parents=True, exist_ok=True)
    py.write_text(
        "#!/bin/sh\n"
        'if [ "${1:-}" = "-c" ]; then exit 0; fi\n'
        'if [ -n "${BOTRELAY_API_KEY:-}" ] || [ -n "${BOTRELAY_VAULT_KEY:-}" ]; then\n'
        "  echo LEAKED >&2\n"
        "fi\n"
        "echo STARTED >&2\n"
        "exit 44\n"
    )
    py.chmod(py.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    env_file = home / ".config" / "botrelay" / "agent.env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text(
        "BOTRELAY_API_KEY=sentinel-api-key\nBOTRELAY_VAULT_KEY=sentinel-vault-key\n"
    )
    env_file.chmod(0o600)
    proc = _run_mcp(tmp_path, home)
    assert proc.returncode == 44, proc.stderr
    assert "STARTED" in proc.stderr
    assert "LEAKED" not in proc.stderr
    assert "sentinel-api-key" not in proc.stdout + proc.stderr
    assert "sentinel-vault-key" not in proc.stdout + proc.stderr


def test_mcp_json_missing_python_names_install_without_secrets(tmp_path: Path) -> None:
    proc = _run_mcp(
        tmp_path,
        tmp_path / "empty-home",
        {
            "BOTRELAY_API_KEY": "sentinel-api-key",
            "BOTRELAY_VAULT_KEY": "sentinel-vault-key",
        },
    )
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert "not importable" in proc.stderr
    assert ".venvs/botrelay" in proc.stderr
    assert "BOTRELAY_PYTHON" in proc.stderr
    assert "sentinel-api-key" not in proc.stderr
    assert "sentinel-vault-key" not in proc.stderr


def test_readme_documents_agent_env_and_launch() -> None:
    readme = (PLUGIN / "README.md").read_text()
    assert "pip install -U botrelay-mcp botrelay-cli" in readme
    assert "botrelay agent configure" in readme
    assert ".config/botrelay/agent.env" in readme
    assert "0600" in readme
    assert "Try in Chat" in readme
    assert "/botrelay-login" in readme
    assert "Log into BotRelay and get the vault information." in readme
    assert "**Configure**" not in readme
    assert "Plugins → Configure" not in readme
    how = readme.split("## How it works", 1)[1].split("## ", 1)[0]
    assert "bash -lc" in how
    assert "botrelay_mcp" in how
    assert "BOTRELAY_PYTHON" in how
    assert "agent.env" in how
    assert "Grok" in how and "Cursor" in how
    assert "$HOME/.venvs/botrelay" in how
    assert "does not use `${CURSOR_PLUGIN_ROOT}`" in how
    assert "does not source `agent.env`" in how
    assert "must load" in how
    assert "not the Marketplace entrypoint" in how
    assert "${CURSOR_PLUGIN_ROOT}/scripts/launch.sh" not in how
    trouble = readme.split("## Troubleshooting", 1)[1]
    assert "./scripts/launch.sh" in trouble
    assert "${PLUGIN_ROOT}" in trouble
    assert "${CURSOR_PLUGIN_ROOT}" in trouble
    assert "Grok leaves `${CURSOR_PLUGIN_ROOT}` unsubstituted" in trouble
    assert "fully quit Cursor and reopen it" in trouble
    assert "Reload Window" in trouble
    assert ".venvs/botrelay/bin/python3" in trouble
    assert "Scripts/python.exe" in trouble
    assert "botrelay agent configure" in trouble
    assert "does not source it" in trouble
    assert "BOTRELAY_PYTHON" in readme
    assert "PATH" in readme
    assert "Shared MCP" in readme
    assert ".venvs/botrelay" in readme
    assert "botrelay-mcp: not found" in readme
    assert "same `mcp.json`" in trouble
    assert "same Marketplace `mcp.json`" in how
    assert "agent token" not in readme.lower()
    assert "API key (`brt_live_…`)" in readme
    grok = readme.split("## Grok Bot", 1)[1].split("## ", 1)[0]
    assert "shared virtual machine" in grok
    assert "own desktop and browser" in grok
    assert "~/.venvs/botrelay" in grok
    assert "~/.config/botrelay/agent.env" in grok
    assert "import botrelay_mcp" in grok
    assert "pip install -U botrelay-mcp botrelay-cli" in grok
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
    assert "[Grok Bot](#grok-bot)" in readme.split("## Grok Bot", 1)[0]
    assert "Works in Cursor, fails in a Grok agent" in trouble
    assert "[Grok Bot](#grok-bot)" in trouble


def test_skill_and_login_teach_grok_vm_onetime_setup() -> None:
    skill = (PLUGIN / "skills" / "botrelay-secrets" / "SKILL.md").read_text()
    command = (PLUGIN / "commands" / "botrelay-login.md").read_text()
    rule = (PLUGIN / "rules" / "botrelay-secrets.mdc").read_text()
    for path, text in (
        ("skill", skill),
        ("command", command),
    ):
        lowered = text.lower()
        assert "agent token" not in lowered, path
        assert "import botrelay_mcp" in text, path
        assert ".config/botrelay/agent.env" in text, path
        assert "pip install -U botrelay-mcp botrelay-cli" in text, path
        assert "https://api.botrelay.ai" in text, path
        assert "API key (`brt_live_…`)" in text, path
        assert "Vault key" in text or "vault key" in text, path
        assert "--api-url" in text and "--api-key" in text and "--vault-key" in text, path
        assert "hand the desktop to the user" in lowered, path
        assert "host secure secret inputs" in lowered, path
        assert "do not use browser form-fill tools to write `agent.env`" in lowered, path
        assert "get_vault" in text, path
        assert "shared virtual machine" in lowered or "share one virtual machine" in lowered, path
        assert "own desktop and browser" in lowered, path
        assert "does not create `agent.env` on the Grok VM" in text, path
        assert "does not create `agent.env` on the Mac" in text, path
        assert "skip install and configure" in lowered, path
        assert "fourth credential" in lowered, path
    assert "agent token" not in rule.lower()
    assert "skip install and configure" in rule.lower()
    assert "API key (`brt_live_…`)" in rule
    assert "does not create `agent.env` on the Grok VM" in rule
    assert "browser form-fill tools to write `agent.env`" in rule.lower()


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
