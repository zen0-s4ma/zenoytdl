from __future__ import annotations

import os
import sys
from pathlib import Path


def make_path_with_fake_binary(fake_bin: Path) -> str:
    return f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}"


def write_fake_ytdl_sub(fake_bin: Path, script_source: str) -> None:
    """Create a cross-platform fake `ytdl-sub` binary in `fake_bin`."""
    fake_bin.mkdir(parents=True, exist_ok=True)

    script_path = fake_bin / "ytdl_sub_fake_impl.py"
    script_path.write_text(script_source, encoding="utf-8")

    if os.name == "nt":
        launcher = fake_bin / "ytdl-sub.cmd"
        launcher.write_text(
            "@echo off\r\n"
            f'"{sys.executable}" "%~dp0ytdl_sub_fake_impl.py" %*\r\n'
            "exit /b %ERRORLEVEL%\r\n",
            encoding="utf-8",
        )
        return

    launcher = fake_bin / "ytdl-sub"
    launcher.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import runpy\n"
        "target = Path(__file__).with_name(\"ytdl_sub_fake_impl.py\")\n"
        "runpy.run_path(str(target), run_name=\"__main__\")\n",
        encoding="utf-8",
    )
    launcher.chmod(0o755)
