from __future__ import annotations

import json
import os
import select
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import IO, Any

import pytest

# This module targets the monorepo layout (plugins/botrelay/tests/test_launch.py).
# The public plugin repo keeps a copy; plugin-local coverage lives in test_mcp_launch.py.
_HERE = Path(__file__).resolve()
if len(_HERE.parents) < 4:
    pytest.skip("monorepo layout required for test_launch.py", allow_module_level=True)

pytest.importorskip("botrelay.crypto")
from botrelay.crypto import random_key, vault_key_to_env  # noqa: E402

REPO = _HERE.parents[3]
PLUGIN = REPO / "plugins" / "botrelay"
LAUNCH = PLUGIN / "scripts" / "launch.sh"
INSTALL = PLUGIN / "scripts" / "install-local.sh"


def _readline(stream: IO[str], timeout: float = 15) -> str:
    ready, _, _ = select.select([stream], [], [], timeout)
    if not ready:
        raise AssertionError("timed out waiting for MCP stdout")
    line = stream.readline()
    if line == "":
        raise AssertionError("MCP stdout closed before the next JSON-RPC frame")
    return line


def _read_frame(stream: IO[str], timeout: float = 15) -> dict[str, Any]:
    while True:
        line = _readline(stream, timeout).strip()
        if line:
            return json.loads(line)


def _stop(proc: subprocess.Popen[str]) -> str:
    if proc.poll() is None:
        proc.terminate()
    try:
        _out, err = proc.communicate(timeout=5)
    except (subprocess.TimeoutExpired, ValueError, BrokenPipeError):
        proc.kill()
        try:
            _out, err = proc.communicate(timeout=5)
        except Exception:
            return ""
    return err or ""


def test_launch_scripts_are_executable() -> None:
    for path in (LAUNCH, INSTALL):
        mode = path.stat().st_mode
        assert mode & stat.S_IXUSR, path


def test_launch_requires_keys(tmp_path: Path) -> None:
    proc = subprocess.run(
        ["bash", str(LAUNCH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={"PATH": os.environ.get("PATH", ""), "HOME": str(tmp_path)},
    )
    assert proc.returncode != 0
    assert proc.stdout == ""
    assert "BOTRELAY_API_KEY" in proc.stderr
    assert "brt_live_" not in proc.stderr


def test_launch_rejects_unsubstituted_placeholders(tmp_path: Path) -> None:
    proc = subprocess.run(
        ["bash", str(LAUNCH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(tmp_path),
            "BOTRELAY_API_URL": "${BOTRELAY_API_URL}",
            "BOTRELAY_API_KEY": "${BOTRELAY_API_KEY}",
            "BOTRELAY_VAULT_KEY": "${BOTRELAY_VAULT_KEY}",
        },
    )
    assert proc.returncode != 0
    assert proc.stdout == ""
    assert "must be set" in proc.stderr
    assert "${BOTRELAY_API_KEY}" not in proc.stderr


def test_launch_prefers_console_script_on_path(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    marker = tmp_path / "console-args"
    console = bin_dir / "botrelay-mcp"
    console.write_text(
        f"#!{sys.executable}\n"
        "import os\n"
        "from pathlib import Path\n"
        "Path(os.environ['BOTRELAY_TEST_MARKER']).write_text(' '.join(os.sys.argv[1:]))\n"
    )
    console.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
            "BOTRELAY_API_KEY": "brt_live_PATH_TEST_KEY",
            "BOTRELAY_VAULT_KEY": vault_key_to_env(random_key()),
            "BOTRELAY_TEST_MARKER": str(marker),
        }
    )
    env.pop("BOTRELAY_PYTHON", None)

    proc = subprocess.run(
        ["bash", str(LAUNCH), "from-console"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
    )

    assert proc.returncode == 0, proc.stderr
    assert marker.read_text() == "from-console"


def test_launch_stdio_initialize_keeps_keys_off_the_wire() -> None:
    api_key = "brt_live_PLUGIN_LAUNCH_TEST_KEY"
    vault_key = vault_key_to_env(random_key())
    env = os.environ.copy()
    env.update(
        {
            "BOTRELAY_API_KEY": api_key,
            "BOTRELAY_VAULT_KEY": vault_key,
            "BOTRELAY_API_URL": "https://api.botrelay.ai",
            "BOTRELAY_PYTHON": sys.executable,
            "PYTHONUNBUFFERED": "1",
        }
    )
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "botrelay-plugin-tests", "version": "0"},
        },
    }
    initialized = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
    tools_list = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    proc = subprocess.Popen(
        ["bash", str(LAUNCH)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=str(REPO),
        bufsize=1,
    )
    assert proc.stdin is not None and proc.stdout is not None
    out_chunks: list[str] = []
    try:
        proc.stdin.write(json.dumps(init) + "\n")
        proc.stdin.flush()
        frame1 = _read_frame(proc.stdout)
        out_chunks.append(json.dumps(frame1))
        assert frame1.get("id") == 1 and "result" in frame1

        proc.stdin.write(json.dumps(initialized) + "\n")
        proc.stdin.write(json.dumps(tools_list) + "\n")
        proc.stdin.flush()
        frame2 = _read_frame(proc.stdout)
        out_chunks.append(json.dumps(frame2))
        assert frame2.get("id") == 2 and "result" in frame2
        names = {tool["name"] for tool in frame2["result"]["tools"]}
        assert names == {"get_vault", "list_secrets", "get_secret"}
    finally:
        err = _stop(proc)

    haystack = "\n".join(out_chunks) + err
    assert api_key not in haystack
    assert vault_key not in haystack


def test_relative_launch_from_repo_root_is_missing() -> None:
    """Cursor Team Marketplace cwd is the checkout; ./scripts/launch.sh is not there."""
    proc = subprocess.run(
        ["bash", "./scripts/launch.sh"],
        cwd=REPO,
        capture_output=True,
        text=True,
        env={"PATH": os.environ.get("PATH", "")},
    )
    assert proc.returncode != 0
    blob = (proc.stderr + proc.stdout).lower()
    assert "no such file" in blob or "not found" in blob
    assert not (REPO / "scripts" / "launch.sh").exists()


def test_install_local_records_checkout(tmp_path: Path) -> None:
    dest = tmp_path / "plugins" / "local" / "botrelay"
    proc = subprocess.run(
        ["bash", str(INSTALL)],
        capture_output=True,
        text=True,
        env={
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(tmp_path),
            "BOTRELAY_PLUGIN_LOCAL_DIR": str(dest),
        },
    )
    assert proc.returncode == 0, proc.stderr
    assert dest.is_dir()
    assert (dest / ".cursor-plugin" / "plugin.json").is_file()
    assert (dest / "scripts" / "launch.sh").is_file()
    assert (dest / ".repo-root").read_text().strip() == str(REPO)
    assert "brt_live_" not in proc.stdout
    assert "brt_live_" not in proc.stderr
    copied_env = dest / ".env"
    assert not copied_env.exists()
    assert "botrelay-mcp on PATH" in proc.stdout
    assert ".repo-root" in proc.stdout


def _keys_env(tmp_path: Path, **extra: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "HOME": os.environ.get("HOME", str(tmp_path)),
            "BOTRELAY_API_KEY": "brt_live_PLUGIN_LAUNCH_TEST_KEY",
            "BOTRELAY_VAULT_KEY": vault_key_to_env(random_key()),
            "BOTRELAY_API_URL": "https://api.botrelay.ai",
        }
    )
    env.pop("BOTRELAY_PYTHON", None)
    env.update(extra)
    return env


def _write_probe(path: Path, marker: str, code: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"REAL={sys.executable!r}\n"
        'if [[ "${1:-}" == "-c" ]]; then\n'
        '  exec "$REAL" "$@"\n'
        "fi\n"
        f"echo {marker!r} >&2\n"
        f"exit {code}\n"
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _write_console_script(path: Path, marker: str, code: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        f"sys.stderr.write({marker!r} + '\\n')\n"
        f"raise SystemExit({code})\n"
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _copied_launcher(tmp_path: Path, repo_root: Path | None = None) -> Path:
    plugin = tmp_path / "plugin"
    (plugin / "scripts").mkdir(parents=True)
    dest = plugin / "scripts" / "launch.sh"
    shutil.copy(LAUNCH, dest)
    dest.chmod(dest.stat().st_mode | stat.S_IXUSR)
    if repo_root is not None:
        (plugin / ".repo-root").write_text(str(repo_root) + "\n")
        (repo_root / "apps" / "mcp" / "src" / "botrelay_mcp").mkdir(parents=True)
    return dest


def test_launch_prefers_botrelay_python_over_path_cmd(tmp_path: Path) -> None:
    python_probe = tmp_path / "custom-python"
    _write_probe(python_probe, "USED_BOTRELAY_PYTHON", 41)
    path_cmd = tmp_path / "bin" / "botrelay-mcp"
    _write_console_script(path_cmd, "USED_PATH_BOTRELAY_MCP", 42)
    proc = subprocess.run(
        ["bash", str(LAUNCH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=_keys_env(
            tmp_path,
            PATH=f"{path_cmd.parent}{os.pathsep}{os.environ.get('PATH', '')}",
            BOTRELAY_PYTHON=str(python_probe),
        ),
    )
    assert proc.returncode == 41, proc.stderr
    assert "USED_BOTRELAY_PYTHON" in proc.stderr
    assert "USED_PATH_BOTRELAY_MCP" not in proc.stderr


def test_launch_skips_empty_botrelay_python(tmp_path: Path) -> None:
    path_cmd = tmp_path / "bin" / "botrelay-mcp"
    _write_console_script(path_cmd, "USED_PATH_BOTRELAY_MCP", 42)
    proc = subprocess.run(
        ["bash", str(LAUNCH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=_keys_env(
            tmp_path,
            PATH=f"{path_cmd.parent}{os.pathsep}{os.environ.get('PATH', '')}",
            BOTRELAY_PYTHON="",
        ),
    )
    assert proc.returncode == 42, proc.stderr
    assert "USED_PATH_BOTRELAY_MCP" in proc.stderr


def test_launch_skips_unsubstituted_botrelay_python(tmp_path: Path) -> None:
    path_cmd = tmp_path / "bin" / "botrelay-mcp"
    _write_console_script(path_cmd, "USED_PATH_BOTRELAY_MCP", 42)
    proc = subprocess.run(
        ["bash", str(LAUNCH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=_keys_env(
            tmp_path,
            PATH=f"{path_cmd.parent}{os.pathsep}{os.environ.get('PATH', '')}",
            BOTRELAY_PYTHON="${BOTRELAY_PYTHON}",
        ),
    )
    assert proc.returncode == 42, proc.stderr
    assert "USED_PATH_BOTRELAY_MCP" in proc.stderr


def test_launch_execs_path_botrelay_mcp_before_checkout_venv(tmp_path: Path) -> None:
    repo = tmp_path / "checkout"
    launch = _copied_launcher(tmp_path, repo)
    venv_py = repo / ".venv" / "bin" / "python"
    _write_probe(venv_py, "USED_CHECKOUT_VENV", 43)
    path_cmd = tmp_path / "bin" / "botrelay-mcp"
    _write_console_script(path_cmd, "USED_PATH_BOTRELAY_MCP", 42)
    proc = subprocess.run(
        ["bash", str(launch)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=_keys_env(
            tmp_path,
            PATH=f"{path_cmd.parent}{os.pathsep}{os.environ.get('PATH', '')}",
        ),
    )
    assert proc.returncode == 42, proc.stderr
    assert "USED_PATH_BOTRELAY_MCP" in proc.stderr
    assert "USED_CHECKOUT_VENV" not in proc.stderr


def test_launch_uses_repo_root_venv_when_no_path_cmd(tmp_path: Path) -> None:
    repo = tmp_path / "checkout"
    launch = _copied_launcher(tmp_path, repo)
    venv_py = repo / ".venv" / "bin" / "python"
    _write_probe(venv_py, "USED_CHECKOUT_VENV", 43)
    proc = subprocess.run(
        ["bash", str(launch)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=_keys_env(
            tmp_path,
            PATH="/usr/bin:/bin",
        ),
    )
    assert proc.returncode == 43, proc.stderr
    assert "USED_CHECKOUT_VENV" in proc.stderr


def test_cursor_mcp_example_uses_pypi_console_script() -> None:
    data = json.loads((REPO / "apps" / "mcp" / "examples" / "cursor-mcp.json").read_text())
    server = data["mcpServers"]["botrelay"]
    assert server["command"] == "botrelay-mcp"
    assert server.get("args", []) == []
    assert "-m" not in server.get("args", [])
    assert ".venv" not in server["command"]
