"""Resolver behavior for marketplace mcp.json and scripts/launch.sh.

Shared MCP often has an empty GUI PATH and does not receive Configure's
BOTRELAY_PYTHON. These tests simulate that spawn.
"""

from __future__ import annotations

import json
import stat
import subprocess
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
MCP_JSON = PLUGIN / "mcp.json"
LAUNCH = PLUGIN / "scripts" / "launch.sh"
API_KEY = "sentinel-api-key"
VAULT_KEY = "sentinel-vault-key"
UNSET = "${BOTRELAY_PYTHON}"


def _mcp_script() -> str:
    server = json.loads(MCP_JSON.read_text())["mcpServers"]["botrelay"]
    assert server["args"][0] == "-c"
    assert server["args"][2] == "botrelay"
    return server["args"][1]


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


def _run_mcp(
    tmp_path: Path,
    *,
    arg: str,
    home: Path | None = None,
    path: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {
        "HOME": str(home or tmp_path),
        "PATH": path if path is not None else "/usr/bin:/bin",
        "BOTRELAY_API_KEY": API_KEY,
        "BOTRELAY_VAULT_KEY": VAULT_KEY,
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", "-c", _mcp_script(), "botrelay", arg],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )


def _assert_no_secrets(proc: subprocess.CompletedProcess[str]) -> None:
    blob = proc.stdout + proc.stderr
    assert API_KEY not in blob
    assert VAULT_KEY not in blob
    assert "exec: botrelay-mcp: not found" not in blob


def test_shared_mcp_without_env_uses_home_venv(tmp_path: Path) -> None:
    home = tmp_path / "home"
    py = home / ".venvs" / "botrelay" / "bin" / "python3"
    _probe(py, "USED_HOME_PYTHON3", 44)
    # Also present, and must lose: PATH console script and generic python3.
    bindir = tmp_path / "bin"
    _probe(bindir / "botrelay-mcp", "USED_PATH_CONSOLE", 42)
    _probe(bindir / "python3", "USED_GENERIC_PYTHON3", 45, import_ok=True)
    proc = _run_mcp(
        tmp_path,
        arg=UNSET,
        home=home,
        path=f"{bindir}:/usr/bin:/bin",
    )
    assert proc.returncode == 44, proc.stderr
    assert "USED_HOME_PYTHON3" in proc.stderr
    assert "USED_PATH_CONSOLE" not in proc.stderr
    assert "USED_GENERIC_PYTHON3" not in proc.stderr
    _assert_no_secrets(proc)


def test_expanded_arg_wins_when_process_env_is_missing(tmp_path: Path) -> None:
    configured = tmp_path / "configured-python"
    _probe(configured, "USED_ARG", 41)
    home = tmp_path / "home"
    _probe(home / ".venvs" / "botrelay" / "bin" / "python3", "USED_HOME", 44)
    proc = _run_mcp(tmp_path, arg=str(configured), home=home)
    assert proc.returncode == 41, proc.stderr
    assert "USED_ARG" in proc.stderr
    assert "USED_HOME" not in proc.stderr
    _assert_no_secrets(proc)


def test_tilde_arg_expands_with_home(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _probe(home / ".venvs" / "botrelay" / "bin" / "python3", "USED_TILDE", 46)
    proc = _run_mcp(
        tmp_path,
        arg="~/.venvs/botrelay/bin/python3",
        home=home,
    )
    assert proc.returncode == 46, proc.stderr
    assert "USED_TILDE" in proc.stderr
    _assert_no_secrets(proc)


def test_env_used_when_arg_is_unsubstituted(tmp_path: Path) -> None:
    configured = tmp_path / "from-env"
    _probe(configured, "USED_ENV", 47)
    home = tmp_path / "home"
    _probe(home / ".venvs" / "botrelay" / "bin" / "python", "USED_HOME_PYTHON", 44)
    proc = _run_mcp(
        tmp_path,
        arg=UNSET,
        home=home,
        extra_env={"BOTRELAY_PYTHON": str(configured)},
    )
    assert proc.returncode == 47, proc.stderr
    assert "USED_ENV" in proc.stderr
    assert "USED_HOME_PYTHON" not in proc.stderr


def test_non_executable_configured_python_falls_through_to_home(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _probe(home / ".venvs" / "botrelay" / "bin" / "python3", "USED_HOME", 44)
    missing = tmp_path / "missing-python"
    proc = _run_mcp(tmp_path, arg=str(missing), home=home)
    assert proc.returncode == 44, proc.stderr
    assert "USED_HOME" in proc.stderr
    assert "not executable" in proc.stderr
    _assert_no_secrets(proc)


def test_home_python_without_module_is_not_executed(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _probe(
        home / ".venvs" / "botrelay" / "bin" / "python3",
        "USED_BROKEN_HOME",
        99,
        import_ok=False,
    )
    bindir = tmp_path / "bin"
    _probe(bindir / "python3", "USED_GENERIC", 45)
    proc = _run_mcp(
        tmp_path,
        arg=UNSET,
        home=home,
        path=f"{bindir}:/usr/bin:/bin",
    )
    assert proc.returncode == 45, proc.stderr
    assert "USED_BROKEN_HOME" not in proc.stderr
    assert "USED_GENERIC" in proc.stderr


def test_path_console_script_when_home_venv_missing(tmp_path: Path) -> None:
    bindir = tmp_path / "bin"
    _probe(bindir / "botrelay-mcp", "USED_PATH_CONSOLE", 42)
    proc = _run_mcp(
        tmp_path,
        arg="",
        home=tmp_path / "empty-home",
        path=f"{bindir}:/usr/bin:/bin",
    )
    assert proc.returncode == 42, proc.stderr
    assert "USED_PATH_CONSOLE" in proc.stderr


def test_missing_interpreter_exits_without_exec_not_found(tmp_path: Path) -> None:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    proc = _run_mcp(
        tmp_path,
        arg=UNSET,
        home=tmp_path / "empty-home",
        path=f"{bindir}:/usr/bin:/bin",
        extra_env={"BOTRELAY_PYTHON": UNSET},
    )
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert ".venvs/botrelay" in proc.stderr
    assert "Shared MCP" in proc.stderr
    _assert_no_secrets(proc)


def _run_launch(
    tmp_path: Path,
    *,
    home: Path,
    path: str,
    extra_env: dict[str, str] | None = None,
    launch: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {
        "HOME": str(home),
        "PATH": path,
        "BOTRELAY_API_URL": "https://api.botrelay.ai",
        "BOTRELAY_API_KEY": API_KEY,
        "BOTRELAY_VAULT_KEY": VAULT_KEY,
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(launch or LAUNCH)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )


def test_launch_sh_uses_home_venv_when_path_and_python_are_unset(tmp_path: Path) -> None:
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
