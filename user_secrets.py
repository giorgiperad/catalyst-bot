"""User-local secrets store.

Persists sensitive per-user values (e.g. API keys) in a JSON file inside the
current OS user's application-data directory.  The file is NEVER written to
the bot directory, so it cannot be accidentally committed, shared via a
network drive, or reused on a different machine or OS account.

Location:
    Windows : %APPDATA%\\ChiaMarketMaker\\user_secrets.json
    macOS   : ~/Library/Application Support/ChiaMarketMaker/user_secrets.json
    Linux   : ~/.config/ChiaMarketMaker/user_secrets.json
"""

from __future__ import annotations

import json
import os
import platform
import threading
from pathlib import Path

_LOCK = threading.Lock()
_APP_NAME = "ChiaMarketMaker"


def _secrets_path() -> Path:
    """Return the full path to the secrets JSON file (does not create it)."""
    system = platform.system()
    if system == "Windows":
        base = os.getenv("APPDATA") or os.path.expanduser("~")
    elif system == "Darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.getenv("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / _APP_NAME / "user_secrets.json"


def _load_locked() -> dict:
    """Read the secrets file.  Must be called while _LOCK is held."""
    path = _secrets_path()
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _save_locked(data: dict) -> None:
    """Write the secrets file.  Must be called while _LOCK is held."""
    path = _secrets_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    # Restrict file permissions to owner only (defense-in-depth for secrets)
    try:
        import os
        os.chmod(path, 0o600)
    except (OSError, AttributeError):
        pass  # Windows may not support chmod; ACLs would be needed there


def get_secret(key: str) -> str:
    """Return the stored value for *key*, or an empty string if not set."""
    with _LOCK:
        return str(_load_locked().get(key) or "")


def set_secret(key: str, value: str) -> None:
    """Persist *value* for *key*.  Passing an empty string removes the entry."""
    with _LOCK:
        data = _load_locked()
        if value:
            data[key] = value
        else:
            data.pop(key, None)
        _save_locked(data)


def apply_to_config(cfg) -> None:
    """Load persisted secrets into *cfg* in-memory (does NOT write to .env).

    Call once at app startup so the rest of the codebase can read secrets
    via the normal cfg attributes without needing to import this module.
    """
    key = get_secret("SPACESCAN_API_KEY")
    if key:
        cfg.SPACESCAN_API_KEY = key
