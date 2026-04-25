"""End-to-end smoke tests for the CATalyst dashboard.

Scope: verify the app boots, the risk disclaimer renders, and the primary
navigation tabs are present. These tests are deliberately Sage-free — they
prove the static UI shell works, which is what breaks most often when the
HTML/JS is refactored.

Run with:

    cd tests
    python -m pytest e2e/test_smoke.py --e2e -v --headed   # watch in browser
    python -m pytest e2e/test_smoke.py --e2e               # headless

Anything that requires a real Sage connection should live in a separate
file (e.g. `test_full_setup.py`) marked accordingly.
"""
from __future__ import annotations

import re

import pytest

from .conftest import dismiss_disclaimer

pytestmark = pytest.mark.e2e


def test_app_loads_with_disclaimer(app_page):
    """The dashboard should boot, render the title, and show the disclaimer."""
    assert app_page.title() == "CATalyst"
    disclaimer_btn = app_page.locator("#startupDisclaimerContinueBtn")
    disclaimer_btn.wait_for(state="visible", timeout=10_000)
    assert disclaimer_btn.is_visible()
    close_btn = app_page.locator("#startupDisclaimerCloseBtn")
    assert close_btn.is_visible()


def test_dismissing_disclaimer_reveals_wallet_connect(app_page):
    """Continuing past the disclaimer should land on the Sage-connect screen."""
    assert dismiss_disclaimer(app_page) is True
    # The wallet-connect screen advertises Sage by name. The exact button
    # text is "Connect to Sage"; assert via accessible-name match so the
    # test doesn't break if the button gets restyled.
    connect = app_page.get_by_role("button", name=re.compile(r"Connect to Sage", re.I))
    connect.first.wait_for(state="visible", timeout=10_000)
    assert connect.first.is_visible()


def test_primary_nav_tabs_present(app_page):
    """Primary nav should be in the DOM even before the user connects a wallet.

    Names are the buttons' accessible names (aria-label), which differ from
    the visible label in a couple of cases ("P&L" → "Profit and loss",
    "Market Intel" → "Market intelligence"). Test against the accessible
    name so screen-reader users and the test stay aligned.
    """
    dismiss_disclaimer(app_page)
    expected = [
        "Dashboard",
        "Offers",
        "Profit and loss",
        "Market intelligence",
        "Settings",
        "Logs",
        "Data reset",
    ]
    for label in expected:
        nav_btn = app_page.get_by_role("button", name=label, exact=True)
        assert nav_btn.count() >= 1, f"nav button '{label}' missing from DOM"


def test_no_console_errors_on_initial_load(app_page):
    """Catch JS console errors that fire just from loading the dashboard."""
    errors: list[str] = []
    app_page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    # Note: cannot use wait_until="networkidle" — the dashboard holds an
    # open SSE connection (`/api/events`) that never goes idle.
    app_page.reload(wait_until="domcontentloaded")
    # Allow a moment for deferred init scripts + the first SSE event to settle.
    app_page.wait_for_timeout(3_000)
    # SSE/network-related errors are expected when there's no real Sage —
    # filter those out so the test is meaningful.
    real_errors = [
        e for e in errors
        if "EventSource" not in e
        and "Failed to fetch" not in e
        and "NetworkError" not in e
        and "ERR_NETWORK" not in e
    ]
    assert not real_errors, f"Unexpected JS console errors: {real_errors}"
