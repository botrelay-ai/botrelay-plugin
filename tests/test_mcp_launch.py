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
