"""Windows-friendly subprocess launch helpers.

These helpers keep console windows from flashing when the desktop app runs
without an attached terminal.
"""

from __future__ import annotations

import os
import subprocess
from typing import Dict, Any


def hidden_subprocess_kwargs(*, detached: bool = False, new_process_group: bool = False) -> Dict[str, Any]:
    """Return subprocess kwargs that suppress Windows console windows.

    On non-Windows platforms this returns an empty dict.
    """
    if os.name != "nt":
        return {}

    creationflags = 0
    if detached:
        creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    else:
        creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if new_process_group:
        creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

    kwargs: Dict[str, Any] = {}
    if creationflags:
        kwargs["creationflags"] = creationflags

    if hasattr(subprocess, "STARTUPINFO"):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
        kwargs["startupinfo"] = startupinfo

    return kwargs
