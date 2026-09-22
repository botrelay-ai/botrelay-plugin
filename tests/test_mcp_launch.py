"""launch.sh resolution when Shared MCP omits BOTRELAY_PYTHON.

Marketplace mcp.json execs this script via ${CURSOR_PLUGIN_ROOT}. Shared MCP's
cwd is the workspace, and that spawn may not receive Configure env.
"""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
LAUNCH = PLUGIN / "scripts" / "launch.sh"
API_KEY = "sentinel-api-key"
VAULT_KEY = "sentinel-vault-key"
UNSET = "${BOTRELAY_PYTHON}"


def _probe(path: Path, marker: str, code: int, *, import_ok: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    import_exit = "0" if import_ok else "1"
    path.write_text(
        "#!/bin/sh\n"
        'if [ "${1:-}" = "-c" ]; then\n'
        f"  exit {import_exit}\n"
        "fi\n"
        f"echo {marker} >&2\n"
        f"exit {code}\n"
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _assert_no_secrets(proc: subprocess.CompletedProcess[str]) -> None:
    blob = proc.stdout + proc.stderr
    assert API_KEY not in blob
    assert VAULT_KEY not in blob
    assert "exec: botrelay-mcp: not found" not in blob


def _run_launch(
    tmp_path: Path,
    *,
    home: Path,
    path: str,
    extra_env: dict[str, str] | None = None,
    launch: Path | None = None,
    include_keys: bool = True,
) -> subprocess.CompletedProcess[str]:
    env = {
        "HOME": str(home),
        "PATH": path,
    }
    if include_keys:
        env.update(
            {
                "BOTRELAY_API_URL": "https://api.botrelay.ai",
                "BOTRELAY_API_KEY": API_KEY,
                "BOTRELAY_VAULT_KEY": VAULT_KEY,
            }
        )
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(launch or LAUNCH)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )


def _write_agent_env(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(0o600)


def _cred_probe(path: Path) -> None:
    """Exit 44 when the process sees EXPECT_* credentials. Never print them."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/bin/sh\n"
        'if [ "${1:-}" = "-c" ]; then\n'
        "  exit 0\n"
        "fi\n"
        "ok=1\n"
        '[ "$BOTRELAY_API_KEY" = "$EXPECT_API_KEY" ] || ok=0\n'
        '[ "$BOTRELAY_VAULT_KEY" = "$EXPECT_VAULT_KEY" ] || ok=0\n'
        '[ "$BOTRELAY_API_URL" = "$EXPECT_API_URL" ] || ok=0\n'
        'if [ "$ok" = 1 ]; then echo CREDS_OK >&2; else echo CREDS_MISMATCH >&2; fi\n'
        "exit 44\n"
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def test_launch_sh_uses_home_python3_when_botrelay_python_is_missing(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _probe(home / ".venvs" / "botrelay" / "bin" / "python3", "USED_LAUNCH_HOME", 44)
    proc = _run_launch(tmp_path, home=home, path="/usr/bin:/bin")
    assert proc.returncode == 44, proc.stderr
    assert "USED_LAUNCH_HOME" in proc.stderr
    _assert_no_secrets(proc)


def test_launch_sh_uses_home_venv_when_botrelay_python_is_unsubstituted(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _probe(home / ".venvs" / "botrelay" / "bin" / "python3", "USED_LAUNCH_HOME", 44)
    proc = _run_launch(
        tmp_path,
        home=home,
        path="/usr/bin:/bin",
        extra_env={"BOTRELAY_PYTHON": UNSET},
    )
    assert proc.returncode == 44, proc.stderr
    assert "USED_LAUNCH_HOME" in proc.stderr
    _assert_no_secrets(proc)


def test_launch_sh_prefers_console_script_over_home_venv(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _probe(home / ".venvs" / "botrelay" / "bin" / "python3", "USED_LAUNCH_HOME", 44)
    bindir = tmp_path / "bin"
    interpreter = tmp_path / "shebang-python"
    _probe(interpreter, "USED_SHEBANG", 40)
    console = bindir / "botrelay-mcp"
    console.parent.mkdir(parents=True, exist_ok=True)
    console.write_text(f"#!{interpreter}\n")
    console.chmod(console.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    proc = _run_launch(
        tmp_path,
        home=home,
        path=f"{bindir}:/usr/bin:/bin",
    )
    assert proc.returncode == 40, proc.stderr
    assert "USED_SHEBANG" in proc.stderr
    assert "USED_LAUNCH_HOME" not in proc.stderr


def test_launch_sh_expands_tilde_botrelay_python(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _probe(home / "py" / "python3", "USED_LAUNCH_TILDE", 48)
    proc = _run_launch(
        tmp_path,
        home=home,
        path="/usr/bin:/bin",
        extra_env={"BOTRELAY_PYTHON": "~/py/python3"},
    )
    assert proc.returncode == 48, proc.stderr
    assert "USED_LAUNCH_TILDE" in proc.stderr


def test_launch_sh_home_venv_before_checkout(tmp_path: Path) -> None:
    plugin = tmp_path / "plugin"
    scripts = plugin / "scripts"
    scripts.mkdir(parents=True)
    launch = scripts / "launch.sh"
    launch.write_text(LAUNCH.read_text())
    launch.chmod(launch.stat().st_mode | stat.S_IXUSR)
    repo = tmp_path / "checkout"
    (repo / "apps" / "mcp" / "src" / "botrelay_mcp").mkdir(parents=True)
    (plugin / ".repo-root").write_text(str(repo) + "\n")
    _probe(repo / ".venv" / "bin" / "python", "USED_CHECKOUT", 43)
    home = tmp_path / "home"
    _probe(home / ".venvs" / "botrelay" / "bin" / "python", "USED_HOME_PY", 44)
    proc = _run_launch(
        tmp_path,
        home=home,
        path="/usr/bin:/bin",
        launch=launch,
    )
    assert proc.returncode == 44, proc.stderr
    assert "USED_HOME_PY" in proc.stderr
    assert "USED_CHECKOUT" not in proc.stderr


def test_launch_sh_failure_does_not_print_secrets(tmp_path: Path) -> None:
    proc = _run_launch(
        tmp_path,
        home=tmp_path / "empty-home",
        path="/usr/bin:/bin",
        extra_env={"BOTRELAY_PYTHON": UNSET},
    )
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert ".venvs/botrelay" in proc.stderr
    _assert_no_secrets(proc)


def test_launch_sh_loads_agent_env_when_keys_unset(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _cred_probe(home / ".venvs" / "botrelay" / "bin" / "python3")
    _write_agent_env(
        home / ".config" / "botrelay" / "agent.env",
        "\n".join(
            [
                "# comment",
                'export BOTRELAY_API_URL="https://api.botrelay.ai"',
                f"BOTRELAY_API_KEY='{API_KEY}'",
                f'BOTRELAY_VAULT_KEY="{VAULT_KEY}"',
                "PATH=/does-not-exist",
                "",
            ]
        ),
    )
    proc = _run_launch(
        tmp_path,
        home=home,
        path="/usr/bin:/bin",
        include_keys=False,
        extra_env={
            "EXPECT_API_KEY": API_KEY,
            "EXPECT_VAULT_KEY": VAULT_KEY,
            "EXPECT_API_URL": "https://api.botrelay.ai",
        },
    )
    assert proc.returncode == 44, proc.stderr
    assert "CREDS_OK" in proc.stderr
    assert "CREDS_MISMATCH" not in proc.stderr
    _assert_no_secrets(proc)


def test_launch_sh_loads_agent_env_over_unsubstituted_placeholders(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _cred_probe(home / ".venvs" / "botrelay" / "bin" / "python3")
    _write_agent_env(
        home / ".config" / "botrelay" / "agent.env",
        f"BOTRELAY_API_URL=https://api.botrelay.ai\nBOTRELAY_API_KEY={API_KEY}\nBOTRELAY_VAULT_KEY={VAULT_KEY}\n",
    )
    proc = _run_launch(
        tmp_path,
        home=home,
        path="/usr/bin:/bin",
        include_keys=False,
        extra_env={
            "BOTRELAY_API_URL": "${BOTRELAY_API_URL}",
            "BOTRELAY_API_KEY": "${BOTRELAY_API_KEY}",
            "BOTRELAY_VAULT_KEY": "${BOTRELAY_VAULT_KEY}",
            "EXPECT_API_KEY": API_KEY,
            "EXPECT_VAULT_KEY": VAULT_KEY,
            "EXPECT_API_URL": "https://api.botrelay.ai",
        },
    )
    assert proc.returncode == 44, proc.stderr
    assert "CREDS_OK" in proc.stderr
    assert "${BOTRELAY_API_KEY}" not in proc.stderr
    _assert_no_secrets(proc)


def test_launch_sh_loads_botrelay_home_agent_env(tmp_path: Path) -> None:
    home = tmp_path / "home"
    botrelay_home = tmp_path / "custom-home"
    _cred_probe(home / ".venvs" / "botrelay" / "bin" / "python3")
    _write_agent_env(
        botrelay_home / "agent.env",
        f"BOTRELAY_API_URL=https://api.botrelay.ai\nBOTRELAY_API_KEY={API_KEY}\nBOTRELAY_VAULT_KEY={VAULT_KEY}\n",
    )
    proc = _run_launch(
        tmp_path,
        home=home,
        path="/usr/bin:/bin",
        include_keys=False,
        extra_env={
            "BOTRELAY_HOME": str(botrelay_home),
            "EXPECT_API_KEY": API_KEY,
            "EXPECT_VAULT_KEY": VAULT_KEY,
            "EXPECT_API_URL": "https://api.botrelay.ai",
        },
    )
    assert proc.returncode == 44, proc.stderr
    assert "CREDS_OK" in proc.stderr
    _assert_no_secrets(proc)


def test_launch_sh_botrelay_home_wins_and_config_fills_gaps(tmp_path: Path) -> None:
    home = tmp_path / "home"
    botrelay_home = tmp_path / "custom-home"
    _cred_probe(home / ".venvs" / "botrelay" / "bin" / "python3")
    _write_agent_env(
        botrelay_home / "agent.env",
        f"BOTRELAY_API_KEY={API_KEY}\nBOTRELAY_VAULT_KEY=from-home-vault\n",
    )
    _write_agent_env(
        home / ".config" / "botrelay" / "agent.env",
        "BOTRELAY_API_KEY=from-config-api\n"
        f"BOTRELAY_VAULT_KEY={VAULT_KEY}\n"
        "BOTRELAY_API_URL=https://from-config.example\n",
    )
    proc = _run_launch(
        tmp_path,
        home=home,
        path="/usr/bin:/bin",
        include_keys=False,
        extra_env={
            "BOTRELAY_HOME": str(botrelay_home),
            "EXPECT_API_KEY": API_KEY,
            "EXPECT_VAULT_KEY": "from-home-vault",
            "EXPECT_API_URL": "https://from-config.example",
        },
    )
    assert proc.returncode == 44, proc.stderr
    assert "CREDS_OK" in proc.stderr
    assert "from-home-vault" not in proc.stderr
    assert "from-config-api" not in proc.stderr
    _assert_no_secrets(proc)


def test_launch_sh_does_not_override_env_or_execute_agent_env(tmp_path: Path) -> None:
    home = tmp_path / "home"
    marker = tmp_path / "pwned"
    bindir = tmp_path / "bin"
    interpreter = tmp_path / "shebang-python"
    _probe(interpreter, "USED_SHEBANG", 40)
    console = bindir / "botrelay-mcp"
    console.parent.mkdir(parents=True, exist_ok=True)
    console.write_text(f"#!{interpreter}\n")
    console.chmod(console.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    _write_agent_env(
        home / ".config" / "botrelay" / "agent.env",
        "\n".join(
            [
                "BOTRELAY_API_KEY=from-file-api",
                "BOTRELAY_VAULT_KEY=from-file-vault",
                "BOTRELAY_API_URL=https://from-file.example",
                "PATH=/does-not-exist",
                f"LD_PRELOAD=$(touch {marker})",
                f"BOTRELAY_PYTHON=$(touch {marker})",
            ]
        )
        + "\n",
    )
    proc = _run_launch(
        tmp_path,
        home=home,
        path=f"{bindir}:/usr/bin:/bin",
        extra_env={"BOTRELAY_PYTHON": UNSET},
    )
    assert proc.returncode == 40, proc.stderr
    assert "USED_SHEBANG" in proc.stderr
    assert not marker.exists()
    _assert_no_secrets(proc)
    assert "from-file-api" not in proc.stdout + proc.stderr
    assert "from-file-vault" not in proc.stdout + proc.stderr


def test_launch_sh_missing_agent_env_points_at_configure(tmp_path: Path) -> None:
    proc = _run_launch(
        tmp_path,
        home=tmp_path / "empty-home",
        path="/usr/bin:/bin",
        include_keys=False,
        extra_env={
            "BOTRELAY_API_KEY": "${BOTRELAY_API_KEY}",
            "BOTRELAY_VAULT_KEY": "${BOTRELAY_VAULT_KEY}",
        },
    )
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert "must be set" in proc.stderr
    assert "botrelay agent configure" in proc.stderr
    assert "agent.env" in proc.stderr
    assert ".venvs/botrelay" in proc.stderr
    assert "botrelay-cli" in proc.stderr
    assert "${BOTRELAY_API_KEY}" not in proc.stderr
    assert API_KEY not in proc.stderr
    assert VAULT_KEY not in proc.stderr


def test_launch_sh_expands_tilde_botrelay_home(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _cred_probe(home / ".venvs" / "botrelay" / "bin" / "python3")
    _write_agent_env(
        home / "botrelay-home" / "agent.env",
        f"BOTRELAY_API_URL=https://api.botrelay.ai\nBOTRELAY_API_KEY={API_KEY}\nBOTRELAY_VAULT_KEY={VAULT_KEY}\n",
    )
    proc = _run_launch(
        tmp_path,
        home=home,
        path="/usr/bin:/bin",
        include_keys=False,
        extra_env={
            "BOTRELAY_HOME": "~/botrelay-home",
            "EXPECT_API_KEY": API_KEY,
            "EXPECT_VAULT_KEY": VAULT_KEY,
            "EXPECT_API_URL": "https://api.botrelay.ai",
        },
    )
    assert proc.returncode == 44, proc.stderr
    assert "CREDS_OK" in proc.stderr
    _assert_no_secrets(proc)


def test_launch_sh_agent_env_keys_are_not_echoed_when_python_missing(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _write_agent_env(
        home / ".config" / "botrelay" / "agent.env",
        f"BOTRELAY_API_KEY={API_KEY}\nBOTRELAY_VAULT_KEY={VAULT_KEY}\n",
    )
    proc = _run_launch(
        tmp_path,
        home=home,
        path="/usr/bin:/bin",
        include_keys=False,
    )
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert "must be set" not in proc.stderr
    assert "not importable" in proc.stderr
    _assert_no_secrets(proc)
