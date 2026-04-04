"""
V2 Startup Test — Verify All Modules Load Correctly

Run this script to check that the V2 bot can start up properly
on your system. It tests:
1. All Python modules import without errors
2. Database creates and initialises
3. Config reads from .env
4. No circular import issues
5. Mock wallet works for simulation

Usage:
    python startup_test.py

If everything passes, you'll see a green summary at the end.
If something fails, it tells you exactly what went wrong.
"""

import sys
import os
import time
import traceback

# Ensure we're running from the project directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Track results
results = []
start_time = time.time()


def test(name, fn):
    """Run a test and record the result."""
    try:
        fn()
        results.append(("PASS", name, ""))
        print(f"  [PASS] {name}")
    except Exception as e:
        results.append(("FAIL", name, str(e)))
        print(f"  [FAIL] {name}")
        print(f"         Error: {e}")
        if "--verbose" in sys.argv:
            traceback.print_exc()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

print("=" * 60)
print("  Chia CAT Market Maker V2 — Startup Test")
print("=" * 60)
print()

# 1. Core module imports
print("--- Module Imports ---")

def test_import_config():
    from config import cfg
    assert cfg is not None
    assert hasattr(cfg, "SPREAD_BPS")
test("Import config.py", test_import_config)

def test_import_database():
    from database import init_database, log_event, get_stats
    assert callable(init_database)
test("Import database.py", test_import_database)

def test_import_price_engine():
    from price_engine import PriceEngine
    assert callable(PriceEngine)
test("Import price_engine.py", test_import_price_engine)

def test_import_offer_manager():
    from offer_manager import OfferManager
    assert callable(OfferManager)
test("Import offer_manager.py", test_import_offer_manager)

def test_import_fill_tracker():
    from fill_tracker import FillTracker
    assert callable(FillTracker)
test("Import fill_tracker.py", test_import_fill_tracker)

def test_import_dexie_manager():
    from dexie_manager import DexieManager
    assert callable(DexieManager)
test("Import dexie_manager.py", test_import_dexie_manager)

def test_import_coin_manager():
    from coin_manager import CoinManager
    assert callable(CoinManager)
test("Import coin_manager.py", test_import_coin_manager)

def test_import_risk_manager():
    from risk_manager import RiskManager
    assert callable(RiskManager)
test("Import risk_manager.py", test_import_risk_manager)

def test_import_sniper():
    from sniper import Sniper
    assert callable(Sniper)
test("Import sniper.py", test_import_sniper)

def test_import_bot_loop():
    from bot_loop import BotLoop
    assert callable(BotLoop)
test("Import bot_loop.py", test_import_bot_loop)

def test_import_api_server():
    from api_server import app, EventBus
    assert app is not None
    assert callable(EventBus)
test("Import api_server.py", test_import_api_server)

def test_import_mock_wallet():
    from mock_wallet import MockWalletState, simulate_fills
    assert callable(MockWalletState)
test("Import mock_wallet.py", test_import_mock_wallet)

print()

# 2. Config loading
print("--- Config Loading ---")

def test_config_values():
    from config import cfg
    # Check some key V2 settings have sensible defaults
    assert cfg.SPREAD_BPS > 0, f"SPREAD_BPS should be > 0, got {cfg.SPREAD_BPS}"
    assert cfg.CAT_ASSET_ID != "", "CAT_ASSET_ID should not be empty"
test("Config values loaded", test_config_values)

def test_config_env_path():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    assert os.path.exists(env_path), f".env file not found at {env_path}"
test(".env file exists", test_config_env_path)

def test_config_to_dict():
    from config import cfg
    d = cfg.to_dict()
    assert isinstance(d, dict), "cfg.to_dict() should return a dict"
    assert len(d) > 10, f"Config should have many keys, got {len(d)}"
test("Config to_dict() works", test_config_to_dict)

print()

# 3. Database
print("--- Database ---")

def test_database_init():
    from database import init_database
    init_database()
test("Database initialises", test_database_init)

def test_database_log():
    from database import log_event
    log_event("info", "startup_test", "Startup test event")
test("Database log_event works", test_database_log)

def test_database_stats():
    from config import cfg
    from database import get_stats
    stats = get_stats(cfg.CAT_ASSET_ID)
    assert isinstance(stats, dict), "get_stats should return a dict"
test("Database get_stats works", test_database_stats)

print()

# 4. Module instantiation
print("--- Module Instantiation ---")

def test_create_price_engine():
    from price_engine import PriceEngine
    pe = PriceEngine()
    assert pe is not None
test("Create PriceEngine", test_create_price_engine)

def test_create_offer_manager():
    from offer_manager import OfferManager
    om = OfferManager()
    assert om is not None
test("Create OfferManager", test_create_offer_manager)

def test_create_fill_tracker():
    from fill_tracker import FillTracker
    ft = FillTracker()
    assert ft is not None
test("Create FillTracker", test_create_fill_tracker)

def test_create_dexie_manager():
    from dexie_manager import DexieManager
    dm = DexieManager()
    assert dm is not None
test("Create DexieManager", test_create_dexie_manager)

def test_create_coin_manager():
    from coin_manager import CoinManager
    cm = CoinManager()
    assert cm is not None
test("Create CoinManager", test_create_coin_manager)

def test_create_risk_manager():
    from risk_manager import RiskManager
    rm = RiskManager()
    assert rm is not None
test("Create RiskManager", test_create_risk_manager)

def test_create_sniper():
    from sniper import Sniper
    s = Sniper()
    assert s is not None
test("Create Sniper", test_create_sniper)

def test_create_bot_loop():
    from bot_loop import BotLoop
    bl = BotLoop()
    assert bl is not None
    assert hasattr(bl, "offer_manager")
    assert hasattr(bl, "risk_manager")
    assert hasattr(bl, "price_engine")
test("Create BotLoop (full wiring)", test_create_bot_loop)

print()

# 5. Mock wallet
print("--- Mock Wallet ---")

def test_mock_wallet_state():
    from mock_wallet import MockWalletState
    s = MockWalletState()
    assert len(s.xch_coins) == 20, f"Expected 20 XCH coins, got {len(s.xch_coins)}"
    assert len(s.cat_coins) == 15, f"Expected 15 CAT coins, got {len(s.cat_coins)}"
test("Mock wallet initial state", test_mock_wallet_state)

def test_mock_create_offer():
    from mock_wallet import create_offer
    res = create_offer({"1": -500000000000, "2": 3000000}, validate_only=False)
    assert res and res.get("success"), f"Mock offer creation failed: {res}"
    assert res.get("trade_id"), "No trade_id returned"
test("Mock create offer", test_mock_create_offer)

def test_mock_get_coins():
    from mock_wallet import get_spendable_coins_rpc
    res = get_spendable_coins_rpc(1)
    assert res and res.get("success"), "Failed to get mock XCH coins"
    coins = res.get("confirmed_records", [])
    assert len(coins) > 0, "No XCH coins returned"
test("Mock get spendable coins", test_mock_get_coins)

def test_mock_cancel_offer():
    from mock_wallet import create_offer, cancel_offer
    res = create_offer({"1": -100000000000, "2": 1000000}, validate_only=False)
    tid = res.get("trade_id")
    cancel_res = cancel_offer(tid)
    assert cancel_res and cancel_res.get("success"), "Mock cancel failed"
test("Mock cancel offer", test_mock_cancel_offer)

def test_mock_fill_simulator():
    from mock_wallet import simulate_fills, state
    # Create several offers first
    from mock_wallet import create_offer
    for _ in range(10):
        create_offer({"1": -100000000000, "2": 1000000}, validate_only=False)
    # Run fill simulation with high probability
    filled = simulate_fills(fill_probability=0.5)
    # With 10 offers and 50% probability, we should get some fills
    # (but it's random, so just check it returns a list)
    assert isinstance(filled, list), "simulate_fills should return a list"
test("Mock fill simulator", test_mock_fill_simulator)

print()

# 6. Key files exist
print("--- File Checks ---")

required_files = [
    "database.py", "config.py", "price_engine.py", "offer_manager.py",
    "fill_tracker.py", "dexie_manager.py", "coin_manager.py",
    "risk_manager.py", "bot_loop.py", "api_server.py", "sniper.py",
    "wallet.py", "wallet_chia.py", "wallet_sage.py",
    "mock_wallet.py", "bot_gui.html", ".env",
    "coin_prep_worker.py",
]

for f in required_files:
    def make_file_test(filename):
        def _test():
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
            assert os.path.exists(path), f"Missing: {filename}"
        return _test
    test(f"File exists: {f}", make_file_test(f))

print()

# 7. Wallet adapter
print("--- Wallet Adapter ---")

def test_wallet_adapter():
    from wallet import get_wallet_type, WALLET_ID_XCH
    wt = get_wallet_type()
    assert wt in ("chia", "sage"), f"Unknown wallet type: {wt}"
    assert isinstance(WALLET_ID_XCH, int), "WALLET_ID_XCH should be int"
test("Wallet adapter loads", test_wallet_adapter)

def test_wallet_chia_import():
    import wallet_chia
    assert hasattr(wallet_chia, "create_offer")
    assert hasattr(wallet_chia, "get_all_offers")
    assert hasattr(wallet_chia, "get_chia_health")
test("wallet_chia.py imports", test_wallet_chia_import)

def test_wallet_sage_import():
    import wallet_sage
    assert hasattr(wallet_sage, "create_offer")
    assert hasattr(wallet_sage, "get_all_offers")
    assert hasattr(wallet_sage, "get_chia_health")
test("wallet_sage.py imports", test_wallet_sage_import)

def test_wallet_sage_functions():
    """Verify Sage has all the same public functions as Chia."""
    import wallet_chia
    import wallet_sage
    # Key functions that all modules depend on
    required_fns = [
        "get_all_offers", "create_offer", "cancel_offer",
        "classify_offers_from_list", "get_chia_health",
        "get_wallet_sync_status", "get_spendable_coins_rpc",
        "split_coins_rpc", "get_wallet_balance", "get_offer_bech32",
        "is_offer_time_expired", "get_offer_expiry_info",
        "cleanup_expired_offers", "cancel_offers_batch",
        "set_quiet_mode", "WALLET_ID_XCH",
    ]
    missing = []
    for fn in required_fns:
        if not hasattr(wallet_sage, fn):
            missing.append(fn)
    assert len(missing) == 0, f"wallet_sage.py missing: {', '.join(missing)}"
test("Sage has all required functions", test_wallet_sage_functions)

print()

# 8. Flask availability
print("--- Dependencies ---")

def test_flask():
    import flask
    assert flask is not None
test("Flask installed", test_flask)

def test_dotenv():
    import dotenv
    assert dotenv is not None
test("python-dotenv installed", test_dotenv)

def test_requests():
    import requests
    assert requests is not None
test("requests installed", test_requests)

def test_decimal():
    from decimal import Decimal
    assert Decimal("0.001") > 0
test("Decimal works", test_decimal)

print()

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

elapsed = time.time() - start_time
passed = sum(1 for r in results if r[0] == "PASS")
failed = sum(1 for r in results if r[0] == "FAIL")
total = len(results)

print("=" * 60)
if failed == 0:
    print(f"  ALL {total} TESTS PASSED in {elapsed:.1f}s")
    print("  V2 bot is ready to run!")
else:
    print(f"  {passed}/{total} passed, {failed} FAILED in {elapsed:.1f}s")
    print()
    print("  Failed tests:")
    for status, name, error in results:
        if status == "FAIL":
            print(f"    - {name}: {error}")
print("=" * 60)

# Exit with error code if any failures
sys.exit(1 if failed > 0 else 0)
