"""
Pytest configuration — test collection, isolation, and encoding settings.

Fixes:
- Excludes standalone diagnostic scripts that crash pytest collection
- Sets UTF-8 encoding for stdout/stderr capture on Windows (prevents
  UnicodeDecodeError from emoji output in print() statements when pytest
  tries to decode its capture buffer with cp1252)
"""

import sys
import os
import io

# ---------------------------------------------------------------------------
# Exclude standalone integration scripts from collection.
# These files contain module-level code (sys.exit, live API calls) that
# crashes pytest's importer. They're meant to be run directly, not via pytest.
# ---------------------------------------------------------------------------
collect_ignore = [
    "test_parallel_offers.py",
    "test_spacescan.py",
    "test_api_data_sources.py",
    "test_all_apis.py",
]

# ---------------------------------------------------------------------------
# Force UTF-8 for pytest's stdout/stderr capture on Windows.
#
# On Windows, the default console encoding is cp1252 (or the OEM code page).
# Our bot code contains emoji (✅, 🎯, 💰, ×) and Unicode math symbols in
# print() statements. When these are captured by pytest, the bytes land in
# the capture buffer. When pytest later tries to decode the buffer as UTF-8
# (for display in its output), an isolated 0x97 continuation byte (part of
# the UTF-8 × sequence \xc3\x97, split across two capture reads) causes
# UnicodeDecodeError inside contextlib._GeneratorContextManager.__exit__,
# appearing as hundreds of spurious "ERROR at setup/teardown" lines.
#
# The os.environ approach doesn't help because Python has already determined
# sys.stdout's encoding at process start. We must reconfigure the actual
# stream objects AND set the env var for any child processes.
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # Reconfigure stdout and stderr to use UTF-8, replacing any bytes that
    # can't be encoded with the Unicode replacement character rather than
    # raising. This covers the case where pytest has NOT yet replaced
    # sys.stdout with its own capture object.
    for _stream_name in ("stdout", "stderr"):
        _stream = getattr(sys, _stream_name, None)
        if _stream is not None and hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        elif _stream is not None and hasattr(_stream, "buffer"):
            try:
                _wrapped = io.TextIOWrapper(
                    _stream.buffer, encoding="utf-8", errors="replace", line_buffering=True
                )
                setattr(sys, _stream_name, _wrapped)
            except Exception:
                pass
