"""Hosted MCP config and the retired local launcher.

Marketplace mcp.json is a remote URL. It does not exec a local interpreter.
"""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
LAUNCH = PLUGIN / "scripts" / "launch.sh"
API_KEY = "sentinel-api-key"
VAULT_KEY = "sentinel-vault-key"


def _run_launch(tmp_path: Path, *, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = {
        "HOME": str(tmp_path / "home"),
        "PATH": "/usr/bin:/bin",
        "BOTRELAY_API_KEY": API_KEY,
        "BOTRELAY_VAULT_KEY": VAULT_KEY,
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(LAUNCH)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )


def test_launch_sh_is_executable() -> None:
    assert LAUNCH.stat().st_mode & stat.S_IXUSR


def test_launch_sh_tombstone_ignores_agent_env_and_secrets(tmp_path: Path) -> None:
    home = tmp_path / "home"
    env_file = home / ".config" / "botrelay" / "agent.env"
    env_file.parent.mkdir(parents=True)
    env_file.write_text(
        f"BOTRELAY_API_KEY={API_KEY}\nBOTRELAY_VAULT_KEY={VAULT_KEY}\n"
    )
    env_file.chmod(0o600)
    proc = _run_launch(
        tmp_path,
        extra_env={
            "HOME": str(home),
            "BOTRELAY_HOME": str(tmp_path / "custom-home"),
            "BOTRELAY_PYTHON": str(tmp_path / "python"),
        },
    )
    assert proc.returncode == 1
    assert proc.stdout == ""
    blob = proc.stderr
    assert "https://api.botrelay.ai/mcp" in blob
    assert "no longer starts a local MCP process" in blob
    assert "agent configure" in blob
    assert "agent decrypt" in blob
    assert API_KEY not in blob
    assert VAULT_KEY not in blob
    text = LAUNCH.read_text()
    assert "botrelay_mcp" not in text
    assert "agent.env" not in text or "load agent.env" in text
    assert "source " not in text
