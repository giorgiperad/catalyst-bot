"""
CATalyst — Desktop Application Entry Point (V4)

This is the main launcher for the desktop app. It:
1. Starts Flask (api_server.py) in a background thread on localhost:5000
2. Creates a PyWebView window that loads the dashboard from Flask
3. Manages the system tray icon (pystray)
4. Handles native notifications (plyer)
5. Manages clean shutdown of all components

The existing Flask+HTML architecture stays fully functional â€” PyWebView
just wraps it in a native window. The JS bridge (app_bridge.py) will
replace HTTP calls in Phase 2, but for Phase 1 everything goes through
Flask as before.

Usage:
    python desktop_app.py          # Normal launch
    python desktop_app.py --dev    # Dev mode (also opens in browser)
    python desktop_app.py --flask  # Flask-only mode (no desktop window)
"""

import sys
import os
import io
import signal
import threading
import time
import argparse
import subprocess

# ---------------------------------------------------------------------------
# Fix Windows cp1252 terminal encoding so emoji in log messages don't crash.
# Forces UTF-8 on stdout/stderr (including sys.__stdout__/__stderr__ used by
# super_log's slog() function).
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    # stdout and __stdout__ share a buffer, so detach old wrapper first
    for _pair in [("stdout", "__stdout__"), ("stderr", "__stderr__")]:
        _st = getattr(sys, _pair[0], None)
        if _st is not None and hasattr(_st, "buffer"):
            _buf = _st.detach()  # disconnect old wrapper without closing buffer
            _wrapped = io.TextIOWrapper(
                _buf, encoding="utf-8", errors="replace",
                line_buffering=True,
            )
            setattr(sys, _pair[0], _wrapped)
            setattr(sys, _pair[1], _wrapped)

# ---------------------------------------------------------------------------
# Early path setup â€” make sure we can import everything from our directory
# ---------------------------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)


def _bundle_path(relative: str) -> str:
    """Return the absolute path to a bundled resource file.

    In a PyInstaller onedir bundle, data files are extracted alongside the
    executable in sys._MEIPASS.  In normal (dev) mode, files live next to
    this script.  Using this helper ensures path resolution is correct in
    both environments.

    Usage:
        path = _bundle_path('bot_gui.html')
        path = _bundle_path('splash.exe')
    """
    base = getattr(sys, '_MEIPASS', APP_DIR)
    return os.path.join(base, relative)


# ---------------------------------------------------------------------------
# Version & constants
# ---------------------------------------------------------------------------
APP_NAME = "CATalyst"
APP_VERSION = "4.0.0"
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 1000
WINDOW_MIN_WIDTH = 1000
WINDOW_MIN_HEIGHT = 700
_CONSOLE_HIDDEN = False
_RESPAWN_ENV = "BOT_GUI_RESPAWNED_UNDER_PYTHONW"

# Window geometry persistence — lives in the user data directory so
# the setting survives installs to read-only locations like Program Files.
try:
    from user_paths import window_state_file as _window_state_file
    _WINDOW_STATE_FILE = _window_state_file()
except Exception:
    _WINDOW_STATE_FILE = os.path.join(APP_DIR, ".window_state.json")


def _load_window_state() -> dict:
    """Return the last saved window size/position, or {} if none."""
    try:
        import json as _json
        if not os.path.exists(_WINDOW_STATE_FILE):
            return {}
        with open(_WINDOW_STATE_FILE, "r", encoding="utf-8") as fh:
            data = _json.load(fh)
        if not isinstance(data, dict):
            return {}
        # Minimal validation — ignore obviously bad values
        width = int(data.get("width", 0) or 0)
        height = int(data.get("height", 0) or 0)
        if width < WINDOW_MIN_WIDTH or height < WINDOW_MIN_HEIGHT:
            return {}
        if width > 8000 or height > 8000:
            return {}
        return {
            "width": width,
            "height": height,
            "x": int(data.get("x", 0) or 0),
            "y": int(data.get("y", 0) or 0),
            "maximized": bool(data.get("maximized", False)),
        }
    except Exception as e:
        print(f"[WINDOW] Could not load window state: {e}", flush=True)
        return {}


def _save_window_state(window) -> None:
    """Persist the current window size/position to disk."""
    if window is None:
        return
    try:
        import json as _json
        state = {
            "width": int(getattr(window, "width", 0) or 0),
            "height": int(getattr(window, "height", 0) or 0),
            "x": int(getattr(window, "x", 0) or 0),
            "y": int(getattr(window, "y", 0) or 0),
        }
        # Skip obviously invalid snapshots (e.g. minimized window reports 0/0)
        if state["width"] < WINDOW_MIN_WIDTH or state["height"] < WINDOW_MIN_HEIGHT:
            return
        with open(_WINDOW_STATE_FILE, "w", encoding="utf-8") as fh:
            _json.dump(state, fh)
    except Exception as e:
        print(f"[WINDOW] Could not save window state: {e}", flush=True)


def _hide_windows_console() -> bool:
    """Hide the parent console window in normal desktop mode.

    This keeps the app GUI-only for day-to-day use on Windows while still
    allowing explicit console mode in dev or Flask-only runs.
    """
    global _CONSOLE_HIDDEN
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
            _CONSOLE_HIDDEN = True
            return True
    except Exception:
        pass
    return False


def _show_fatal_error_dialog(message: str):
    """Show a native fatal error dialog when no console is visible."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, APP_NAME, 0x10)
            return
        except Exception:
            pass
    print(message)


def _get_pythonw_executable() -> str:
    """Find a matching pythonw.exe for the current interpreter."""
    if sys.platform != "win32":
        return ""
    exe = os.path.abspath(sys.executable or "")
    base = os.path.basename(exe).lower()
    if base == "pythonw.exe":
        return exe
    candidate = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.exists(candidate):
        return candidate
    return ""


def _respawn_under_pythonw() -> bool:
    """Restart the app under pythonw so no console is created at all.

    Hiding a console after launch still leaves a Windows taskbar entry when the
    process itself was started by python.exe. Relaunching under pythonw avoids
    creating that console in the first place.
    """
    if sys.platform != "win32":
        return False
    if os.environ.get(_RESPAWN_ENV) == "1":
        return False
    if os.path.basename(sys.executable or "").lower() == "pythonw.exe":
        return False

    pythonw = _get_pythonw_executable()
    if not pythonw:
        return False

    env = os.environ.copy()
    env[_RESPAWN_ENV] = "1"
    creationflags = 0
    for flag_name in ("DETACHED_PROCESS", "CREATE_NEW_PROCESS_GROUP"):
        creationflags |= getattr(subprocess, flag_name, 0)

    cmd = [pythonw, os.path.abspath(__file__), *sys.argv[1:]]
    try:
        subprocess.Popen(
            cmd,
            cwd=APP_DIR,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        return True
    except Exception:
        return False


def check_port_free(port: int) -> bool:
    """Check if localhost port is available. Returns True if free."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(1)
        sock.connect(("127.0.0.1", port))
        sock.close()
        return False  # Port is in use
    except (ConnectionRefusedError, OSError, socket.timeout):
        return True  # Port is free
    finally:
        try:
            sock.close()
        except Exception:
            pass


def wait_for_flask(timeout: float = 15.0) -> bool:
    """Wait for Flask to start accepting connections. Returns True if ready."""
    import socket
    start = time.time()
    while time.time() - start < timeout:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(1)
            sock.connect((FLASK_HOST, FLASK_PORT))
            sock.close()
            return True
        except (ConnectionRefusedError, OSError, socket.timeout):
            time.sleep(0.3)
        finally:
            try:
                sock.close()
            except Exception:
                pass
    return False


def start_flask_server():
    """
    Start the Flask API server in the current thread.
    This runs in a daemon thread so it dies when the main process exits.
    """
    # Import api_server â€” this triggers all the module imports and init
    import api_server

    # Initialise database
    from database import init_database
    init_database()

    # Create bot instance
    api_server.create_bot()

    # Start wallet startup manager (sage_node handles wallet startup orchestration).
    # For Sage: manages the connecting â†’ launching â†’ fingerprint â†’ ready flow.
    # The GUI's startup screen polls /api/sage/startup-status which depends on this.
    try:
        import sage_node
        sage_node.start_preload()
    except Exception as e:
        print(f"  Warning: Wallet startup manager failed: {e}")

    # Restore log clear-point from database
    try:
        from database import get_setting
        saved = get_setting("logs_cleared_at")
        if saved:
            api_server._logs_cleared_at = saved
    except Exception:
        pass

    # Restore fresh-run cutoff so PnL/history stay scoped to the current run
    try:
        restored_cutoff = api_server._restore_run_history_cutoff_from_events()
        if restored_cutoff:
            print(f"  [Fresh Run] Restored history cutoff: {restored_cutoff}")
    except Exception:
        pass

    # Run Flask (this blocks until shutdown)
    from database import log_event
    log_event("info", "server_started", f"Desktop app v{APP_VERSION} starting Flask on port {FLASK_PORT}")

    api_server.app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=False,
        threaded=True,
        use_reloader=False  # Important: don't use reloader in desktop mode
    )


def run_desktop_mode(dev_mode: bool = False):
    """Main desktop app flow."""
    try:
        import webview
    except ImportError:
        print("\n  ERROR: pywebview is not installed.")
        print("  Install it with: pip install pywebview --break-system-packages")
        print("  Running in Flask-only mode instead.\n")
        run_flask_mode()
        return

    print(f"\n  {APP_NAME} v{APP_VERSION}")
    print(f"  {'=' * 40}")

    # Check port
    if not check_port_free(FLASK_PORT):
        print(f"\n  Port {FLASK_PORT} is already in use!")
        print(f"  Close the other instance first.")
        sys.exit(1)

    # Start Flask in background thread
    print(f"  Starting Flask server on port {FLASK_PORT}...")
    flask_thread = threading.Thread(target=start_flask_server, daemon=True, name="FlaskServer")
    flask_thread.start()

    # Wait for Flask to be ready
    print(f"  Waiting for Flask to accept connections...")
    if not wait_for_flask(timeout=20.0):
        print(f"\n  ERROR: Flask didn't start within 20 seconds.")
        print(f"  Check the console output above for errors.")
        sys.exit(1)

    print(f"  Flask is ready.")

    # Start system tray in background
    tray_thread = None
    try:
        from tray_manager import TrayManager
        tray = TrayManager(app_name=APP_NAME, app_version=APP_VERSION)
        tray_thread = threading.Thread(target=tray.run, daemon=True, name="SystemTray")
        tray_thread.start()
        print(f"  System tray icon active.")
    except ImportError:
        print(f"  System tray disabled (pystray not installed).")
        tray = None
    except Exception as e:
        print(f"  System tray failed: {e}")
        tray = None

    # Start notification manager
    try:
        from notification_manager import NotificationManager
        notifier = NotificationManager(app_name=APP_NAME)
        print(f"  Notifications enabled.")
    except ImportError:
        print(f"  Notifications disabled (plyer not installed).")
        notifier = None
    except Exception as e:
        print(f"  Notifications failed: {e}")
        notifier = None

    # Wire up tray callbacks
    if tray:
        tray.on_show_dashboard = lambda: _show_window(webview)
        # Tray "Exit" now routes through the SAME graceful shutdown as the
        # in-window X button: show the window, trigger the shutdown modal,
        # and let the user confirm (or cancel) offer cancellation. This
        # removes the previous inconsistency where tray exit silently
        # bypassed the shutdown confirmation.
        tray.on_quit = lambda: _tray_graceful_quit(webview, tray)

        # Phase 3: Start / Stop from tray — call Flask API and show window
        # Read the auth token from the environment (set by api_server at import time).
        _tray_token = os.environ.get("BOT_LOCAL_WRITE_TOKEN", "")

        def _tray_start_bot():
            """Start bot from tray: call Flask, then bring window to front."""
            try:
                import urllib.request
                req = urllib.request.Request(
                    f"http://{FLASK_HOST}:{FLASK_PORT}/api/bot/start",
                    data=b"{}",
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "X-Bot-Local-Token": _tray_token,
                    }
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    _ = resp.read()
            except Exception as e:
                print(f"[TRAY] Start bot failed: {e}", flush=True)
            _show_window(webview)

        def _tray_stop_bot():
            """Stop bot from tray: call Flask."""
            try:
                import urllib.request
                req = urllib.request.Request(
                    f"http://{FLASK_HOST}:{FLASK_PORT}/api/bot/stop",
                    data=b"{}",
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "X-Bot-Local-Token": _tray_token,
                    }
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    _ = resp.read()
            except Exception as e:
                print(f"[TRAY] Stop bot failed: {e}", flush=True)

        tray.on_start_bot = _tray_start_bot
        tray.on_stop_bot = _tray_stop_bot

    # Wire up notifier to bot events (if both available)
    if notifier:
        _wire_notifications(notifier)

    # Phase 3: Start tray status poller — polls /api/status every 10s
    # and calls tray.update_tray_state() so the icon/tooltip/menu stay current.
    if tray:
        tray_poll_thread = threading.Thread(
            target=_poll_tray_status,
            args=(tray,),
            daemon=True,
            name="TrayStatusPoller"
        )
        tray_poll_thread.start()

    print(f"\n  Launching desktop window...")
    if dev_mode:
        print(f"  Dev mode: also accessible at http://{FLASK_HOST}:{FLASK_PORT}/")

    # Create JS bridge for window.pywebview.api calls
    try:
        from app_bridge import AppBridge
        bridge = AppBridge()
        print(f"  JS bridge ready (AppBridge).")
    except Exception as e:
        print(f"  Warning: JS bridge failed to load: {e}")
        bridge = None

    # Restore last-saved window geometry if we have one
    _saved_state = _load_window_state()
    _win_width  = _saved_state.get("width",  WINDOW_WIDTH)
    _win_height = _saved_state.get("height", WINDOW_HEIGHT)
    _win_x      = _saved_state.get("x")
    _win_y      = _saved_state.get("y")

    # Show a local splash page first (logo + "created by MonkeyZoo") so the
    # window doesn't flash black while the WebView2 backend boots and Flask's
    # first HTML render lands. The splash auto-redirects to the Flask URL
    # after a brief delay (see splash.html).
    _splash_path = _bundle_path("splash.html")
    if os.path.exists(_splash_path):
        _initial_url = "file:///" + _splash_path.replace("\\", "/")
    else:
        _initial_url = f"http://{FLASK_HOST}:{FLASK_PORT}/"

    _create_window_kwargs = dict(
        title=APP_NAME,
        url=_initial_url,
        js_api=bridge,
        width=_win_width,
        height=_win_height,
        min_size=(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT),
        resizable=True,
        frameless=True,
        shadow=True,
        easy_drag=False,
        text_select=False,
        background_color="#0B0E14",
    )
    # Only pass x/y if we actually have a saved position — PyWebView will
    # centre on primary display otherwise, which is the correct default.
    if _win_x is not None and _win_y is not None:
        _create_window_kwargs["x"] = _win_x
        _create_window_kwargs["y"] = _win_y

    window = webview.create_window(**_create_window_kwargs)

    # Close button = graceful shutdown (stop bot, kill Flask, exit).
    # We also snapshot the window geometry here so the next launch
    # restores the same size/position.
    #
    # Alt+F4 protection: if the bot is running and the user has not yet
    # acknowledged the shutdown modal, we cancel the close and bounce
    # through the in-GUI modal first. Only when the modal has finished
    # its graceful sequence (and sets _state["confirmed_close"]=True) do
    # we let the window actually close.
    _state["confirmed_close"] = False

    def on_closing():
        # If the user already confirmed via the modal, let it through.
        if _state.get("confirmed_close"):
            try:
                _save_window_state(window)
            except Exception:
                pass
            _cleanup()
            if tray:
                try:
                    tray.stop()
                except Exception:
                    pass
            return True

        # Check whether the bot is actually running. If not, we can
        # close immediately — there's nothing to gracefully shut down.
        bot_running = False
        try:
            import api_server as _api
            if _api.bot and getattr(_api.bot, "_running", False):
                bot_running = True
        except Exception:
            pass

        if not bot_running:
            # Safe path — save state and close.
            try:
                _save_window_state(window)
            except Exception:
                pass
            _cleanup()
            if tray:
                try:
                    tray.stop()
                except Exception:
                    pass
            return True

        # Bot is running — route through the in-GUI shutdown modal.
        try:
            window.show()
            window.restore()
            window.evaluate_js("window.showShutdownModal && window.showShutdownModal();")
            print("\n  Alt+F4 intercepted — showing shutdown confirmation.", flush=True)
        except Exception as e:
            print(f"  [CLOSE] Could not show shutdown modal: {e}", flush=True)
            # Fall back to hard close so the user isn't trapped
            try:
                _save_window_state(window)
            except Exception:
                pass
            _cleanup()
            return True
        # Cancel this close event — the modal will set confirmed_close
        # and re-invoke the close when it finishes the graceful sequence.
        return False

    window.events.closing += on_closing
    # Expose the confirm flag to the JS side via the bridge.
    # The shutdown modal's "Shutdown App" button sets this before
    # re-triggering close, so a second on_closing() call is honoured.
    if bridge is not None:
        try:
            bridge._set_confirmed_close = lambda: _state.update({"confirmed_close": True})
        except Exception:
            pass

    # Store window reference for tray callbacks
    _state["window"] = window
    _state["tray"] = tray
    _state["notifier"] = notifier

    # Start PyWebView event loop (blocks until all windows closed)
    webview.start(
        debug=dev_mode,
        gui=_detect_gui_backend(),
        http_server=False,  # We run our own Flask server
    )

    # If we get here, all windows are closed
    print("\n  Desktop window closed.")
    print("  Stopping bot...", flush=True)
    _cleanup()
    print("  Shutdown complete. Goodbye!", flush=True)
    time.sleep(0.5)  # Brief pause so user can see the shutdown messages
    os._exit(0)  # Force exit â€” daemon threads (Flask, tray) won't block


def run_flask_mode():
    """Fallback: run as plain Flask server (like v3)."""
    print(f"\n  {APP_NAME} v{APP_VERSION} â€” Flask Mode")
    print(f"  {'=' * 40}")
    print(f"  Open http://{FLASK_HOST}:{FLASK_PORT}/ in your browser")
    print(f"  Press Ctrl+C to stop\n")

    if not check_port_free(FLASK_PORT):
        print(f"  Port {FLASK_PORT} is already in use!")
        sys.exit(1)

    # Register signal handlers
    signal.signal(signal.SIGINT, lambda s, f: _cleanup())
    signal.signal(signal.SIGTERM, lambda s, f: _cleanup())
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, lambda s, f: _cleanup())

    start_flask_server()


# ---------------------------------------------------------------------------
# Internal state & helpers
# ---------------------------------------------------------------------------
_state = {
    "window": None,
    "tray": None,
    "notifier": None,
}


def _detect_gui_backend():
    """Detect best PyWebView GUI backend for the current platform."""
    if sys.platform == "win32":
        return "edgechromium"  # Edge WebView2 â€” best on Windows
    elif sys.platform == "darwin":
        return None  # Default WebKit on macOS
    else:
        return None  # Default GTK WebKit on Linux


def _show_window(webview_module):
    """Show/focus the main window (called from tray)."""
    window = _state.get("window")
    if window:
        try:
            window.show()
            window.restore()
        except Exception:
            pass


def _quit_app(webview_module, tray):
    """Clean shutdown from tray quit action (fallback for non-graceful paths)."""
    _cleanup()
    try:
        # Destroy all webview windows
        for win in webview_module.windows:
            win.destroy()
    except Exception:
        pass
    if tray:
        tray.stop()
    # Force exit after brief cleanup window
    threading.Timer(2.0, lambda: os._exit(0)).start()


def _tray_graceful_quit(webview_module, tray):
    """Tray-initiated graceful quit.

    Shows the main window and triggers the in-GUI shutdown modal via the
    JS bridge.  If the window/bridge isn't available, falls back to the
    older hard _quit_app path.  This way tray Exit behaves exactly like
    clicking the X button in the custom titlebar — letting users cancel
    offers first if the bot is running.
    """
    window = _state.get("window")
    if not window:
        # No window — nothing to show, just quit.
        _quit_app(webview_module, tray)
        return

    try:
        # Bring the window up so the modal is visible.
        window.show()
        window.restore()
    except Exception:
        pass

    try:
        # Trigger the same shutdown modal the X button uses.
        window.evaluate_js(
            "window.showShutdownModal && window.showShutdownModal();"
        )
    except Exception as e:
        print(f"[TRAY] Graceful quit via JS bridge failed: {e}", flush=True)
        _quit_app(webview_module, tray)


def _cleanup():
    """Clean shutdown of bot and modules."""
    try:
        import api_server
        if api_server.bot and api_server.bot._running:
            print("  Stopping bot...")
            api_server.bot.stop()
    except Exception:
        pass

    try:
        from database import log_event
        log_event("info", "app_shutdown", f"Desktop app v{APP_VERSION} shutting down")
    except Exception:
        pass


def _poll_tray_status(tray, interval: float = 3.0):
    """
    Phase 3: Background thread that polls /api/status every `interval` seconds
    and calls tray.update_tray_state() to keep the icon/tooltip/menu current.

    Maps bot running state → tray status:
        running=True, circuit_breaker=False  → "running"
        running=True, circuit_breaker=True   → "warning"
        running=False                        → "stopped"
        HTTP error / Flask not up            → keeps last known state
    """
    import urllib.request
    import json as _json

    last_status = "stopped"

    while True:
        try:
            req = urllib.request.Request(
                f"http://{FLASK_HOST}:{FLASK_PORT}/api/status",
                headers={"Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = _json.loads(resp.read().decode())

            running = bool(data.get("running", False))
            cb_tripped = bool(data.get("circuit_breaker_tripped", False))

            # Derive tray status
            if running and cb_tripped:
                new_status = "warning"
            elif running:
                new_status = "running"
            else:
                new_status = "stopped"

            # Active CAT name for tooltip (e.g. "MZ")
            cat_name = ""
            cat_info = data.get("current_cat") or {}
            cat_name = (
                cat_info.get("ticker_id")
                or cat_info.get("name")
                or ""
            )
            if not cat_name:
                # Fallback: check top-level fields some status endpoints return
                cat_name = data.get("cat_ticker") or data.get("cat_name") or ""

            if new_status != last_status or cat_name:
                tray.update_tray_state(new_status, cat_name=cat_name)
                last_status = new_status

        except Exception:
            pass   # Flask not ready or transient error — keep last state

        time.sleep(interval)


def _wire_notifications(notifier):
    """
    Wire the notification manager to bot events.
    This hooks into the SSE EventBus so notifications fire on fills, errors, etc.
    """
    try:
        import api_server
        bus = getattr(api_server, "events", None)
        if bus and hasattr(bus, "subscribe"):
            # Subscribe to fill events
            def on_fill(data):
                side = data.get("side", "?")
                amount = data.get("amount", "?")
                price = data.get("price", "?")
                notifier.notify(
                    title="Offer Filled",
                    message=f"{side.upper()}: {amount} at {price}",
                    category="fill"
                )
            bus.subscribe("fill", on_fill)

            # Subscribe to error events
            def on_error(data):
                msg = data.get("message", "Unknown error")
                notifier.notify(
                    title="Bot Error",
                    message=msg,
                    category="error"
                )
            bus.subscribe("critical", on_error)
    except Exception:
        pass  # Non-critical â€” app works fine without notification wiring


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main(argv=None):
    """Desktop app entry point for both .py and .pyw launchers."""
    parser = argparse.ArgumentParser(description=f"{APP_NAME} v{APP_VERSION}")
    parser.add_argument("--dev", action="store_true", help="Enable dev mode (browser accessible + debug)")
    parser.add_argument("--flask", action="store_true", help="Flask-only mode (no desktop window)")
    parser.add_argument("--show-console", action="store_true", help="Keep the Windows console visible in desktop mode")
    args = parser.parse_args(argv)

    if not args.flask and not args.dev and not args.show_console:
        if _respawn_under_pythonw():
            return 0

    if not args.flask and not args.dev and not args.show_console:
        _hide_windows_console()

    try:
        if args.flask:
            run_flask_mode()
        else:
            run_desktop_mode(dev_mode=args.dev)
        return 0
    except Exception as e:
        # Log crash to file so we can diagnose even if console is hidden.
        # The crash log lives under the user data directory so it's
        # writable regardless of install location.
        import traceback
        try:
            from user_paths import crash_log_file
            crash_log = crash_log_file()
        except Exception:
            crash_log = os.path.join(APP_DIR, "crash.log")

        # Capture the full traceback as a string so we can include it
        # in the crash dialog as well as the file.
        tb_str = traceback.format_exc()

        # Write the crash log — UTF-8 encoded with ASCII-safe fallbacks
        # so the handler itself never crashes on cp1252 Windows locales.
        try:
            with open(crash_log, "w", encoding="utf-8", errors="replace") as f:
                f.write("CATalyst V4 - Crash Report\n")
                f.write("=" * 50 + "\n")
                f.write(f"Time:    {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Version: {APP_VERSION}\n")
                f.write(f"Python:  {sys.version}\n")
                f.write(f"Platform: {sys.platform}\n")
                f.write(f"Install: {APP_DIR}\n")
                try:
                    from user_paths import data_dir as _dd
                    f.write(f"Data:    {_dd()}\n")
                except Exception:
                    pass
                f.write("\n")
                f.write(f"Error: {e}\n\n")
                f.write("Traceback:\n")
                f.write(tb_str)
        except Exception as write_err:
            # Last-ditch: if we can't write the log file, at least print
            # the traceback to stderr so `--show-console` users see it.
            print(f"[CRASH] Could not write crash log to {crash_log}: {write_err}",
                  file=sys.stderr, flush=True)
            print(tb_str, file=sys.stderr, flush=True)

        # Build a user-friendly message for the fatal dialog. Include
        # the actual error text (not just the filename) so the user can
        # read what went wrong without hunting for the log file.
        short_err = str(e)[:300]
        fatal_msg = (
            f"The app crashed on startup.\n\n"
            f"Error: {short_err}\n\n"
            f"A full crash report has been saved to:\n{crash_log}\n\n"
            f"If this keeps happening, please send the crash.log file to "
            f"support so we can diagnose the issue."
        )

        if _CONSOLE_HIDDEN:
            _show_fatal_error_dialog(fatal_msg)
        else:
            print(f"\n  CRASH: {e}")
            print(f"  {tb_str}")
            print(f"  Details saved to: {crash_log}")
            try:
                input("\n  Press Enter to close...")
            except (EOFError, KeyboardInterrupt):
                pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
