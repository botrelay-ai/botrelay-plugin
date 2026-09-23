"""Retired local launcher.

The public plugin and a monorepo copy of this file both live next to
``scripts/launch.sh``. Marketplace MCP is hosted HTTP. This module checks
that the old stdio launcher stays fail-closed and does not start a server.
"""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
LAUNCH = PLUGIN / "scripts" / "launch.sh"
API_KEY = "sentinel-api-key"
VAULT_KEY = "sentinel-vault-key"


def test_launch_script_is_executable() -> None:
    mode = LAUNCH.stat().st_mode
    assert mode & stat.S_IXUSR


def test_launch_is_tombstoned(tmp_path: Path) -> None:
    proc = subprocess.run(
        ["bash", str(LAUNCH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(tmp_path),
            "BOTRELAY_API_KEY": API_KEY,
            "BOTRELAY_VAULT_KEY": VAULT_KEY,
            "BOTRELAY_API_URL": "https://api.botrelay.ai",
        },
    )
    assert proc.returncode == 1
    assert proc.stdout == ""
    err = proc.stderr
    assert "https://api.botrelay.ai/mcp" in err
    assert "botrelay-cli" in err
    assert "agent decrypt" in err
    assert "agent get" in err
    assert "BOTRELAY_API_KEY" in err
    assert "Plugins → Configure" in err
    assert "botrelay-mcp is deprecated" in err
    assert API_KEY not in err
    assert VAULT_KEY not in err
    assert "python -m botrelay_mcp" not in LAUNCH.read_text()
    assert "python -m botrelay_mcp" not in err
