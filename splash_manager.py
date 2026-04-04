"""
V3 Splash Manager — Decentralized Offer Broadcasting via Splash Network

Splash is Dexie's peer-to-peer network for sharing offers across the
Chia ecosystem. Every connected peer receives all offers — wider
distribution means more fill opportunities.

Splash runs as a separate Rust binary alongside the bot. We communicate
via its local HTTP endpoint:
  - Submit offers: POST {"offer": "offer1..."} to SPLASH_SUBMIT_URL
  - Receive offers: Splash POSTs incoming offers to our webhook

This module follows the same queue+flush+dedup pattern as dexie_manager.py
for consistency. It runs alongside Dexie posting, not instead of it.

Usage:
    from splash_manager import SplashManager
    manager = SplashManager()
    manager.queue_post(offer_bech32, trade_id)
    manager.flush_queue()

Requires: Splash binary running locally
    splash.exe --listen-offer-submission 0.0.0.0:4000 \
               --listen-address /ip4/0.0.0.0/tcp/11511
"""

import time
import hashlib
import requests
import threading
from typing import Dict, List, Optional

from config import cfg
from database import log_event


class SplashManager:
    """Manages broadcasting offers to the Splash P2P network.

    Key responsibilities:
    - Queue offers for broadcasting (same interface as DexieManager)
    - Post to Splash's local HTTP endpoint with retries
    - Track posted fingerprints (prevent duplicate broadcasts)
    - Report posting statistics for the GUI
    """

    def __init__(self):
        # Post queue (cleared after each flush)
        self._queue: List[Dict] = []

        # Fingerprints of already-posted offers (sha256 of bech32 string)
        self._posted_fingerprints: set = set()

        # Lock for thread safety
        self._lock = threading.Lock()

        # Stats
        self._total_posted: int = 0
        self._total_failed: int = 0
        self._total_skipped: int = 0

        # Track whether Splash is reachable (avoid spamming logs)
        self._splash_healthy: bool = True
        self._consecutive_failures: int = 0
        self._max_silent_failures: int = 5  # Only log every Nth failure

    # -------------------------------------------------------------------
    # Queue management
    # -------------------------------------------------------------------

    def queue_post(self, offer_bech32: str, trade_id: str = None,
                   force: bool = False):
        """Queue an offer for broadcasting to Splash.

        Args:
            offer_bech32: The offer1... bech32 string
            trade_id: Chia trade_id (for logging/tracking)
            force: If True, post even if fingerprint matches
        """
        if not offer_bech32 or not isinstance(offer_bech32, str):
            return

        with self._lock:
            self._queue.append({
                "offer": offer_bech32.strip(),
                "trade_id": trade_id,
                "force": force,
            })

    def flush_queue(self, flush_all: bool = False) -> Dict:
        """Broadcast all queued offers to Splash.

        Returns summary: {posted: N, failed: N, skipped: N}
        """
        if not getattr(cfg, "SPLASH_ENABLED", False):
            return {"posted": 0, "failed": 0, "skipped": 0, "disabled": True}

        # Grab items from queue
        with self._lock:
            if flush_all:
                batch = list(self._queue)
                self._queue = []
            else:
                max_posts = getattr(cfg, "MAX_POSTS_PER_LOOP", 30)
                batch = list(self._queue[:max_posts])
                self._queue = self._queue[max_posts:]

        if not batch:
            return {"posted": 0, "failed": 0, "skipped": 0}

        posted = 0
        failed = 0
        skipped = 0

        # Cap per loop (same pattern as Dexie — don't block the main loop)
        def _process_one(item):
            offer_bech32 = item["offer"]
            trade_id = item.get("trade_id")
            force = item.get("force", False)
            return self._post_single(offer_bech32, trade_id, force)

        if len(batch) > 10:
            from concurrent.futures import ThreadPoolExecutor, as_completed

            workers = min(8, len(batch))
            log_event("info", "splash_flush_parallel",
                      f"Parallel Splash flush: {len(batch)} offers with {workers} workers")
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(_process_one, item): item for item in batch}
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result.get("skipped"):
                            skipped += 1
                            self._total_skipped += 1
                        elif result.get("success"):
                            posted += 1
                            self._total_posted += 1
                        else:
                            failed += 1
                            self._total_failed += 1
                    except Exception as e:
                        log_event("warning", "splash_parallel_error",
                                  f"Parallel Splash post failed: {e}")
                        failed += 1
                        self._total_failed += 1
        else:
            for item in batch:
                result = _process_one(item)
                if result.get("skipped"):
                    skipped += 1
                    self._total_skipped += 1
                elif result.get("success"):
                    posted += 1
                    self._total_posted += 1
                else:
                    failed += 1
                    self._total_failed += 1

        summary = {"posted": posted, "failed": failed, "skipped": skipped}
        if posted > 0:
            log_event("info", "splash_flush",
                      f"Broadcast {posted} queued offers to Splash "
                      f"({skipped} skipped, {failed} failed)")
        return summary

    # -------------------------------------------------------------------
    # Core posting
    # -------------------------------------------------------------------

    def _post_single(self, offer_bech32: str, trade_id: str = None,
                     force: bool = False) -> Dict:
        """Post a single offer to Splash with retries.

        Returns result dict with success/skipped/error fields.
        """
        # Validate bech32 format
        if not offer_bech32.lower().startswith("offer1"):
            return {"success": False, "error": "not_bech32_offer1"}

        # Fingerprint check (prevent duplicate broadcasts) — lock-protected
        # to prevent race condition when flush_queue uses ThreadPoolExecutor
        fp = self._fingerprint(offer_bech32)
        with self._lock:
            if not force and fp in self._posted_fingerprints:
                return {"success": True, "skipped": True, "reason": "already_broadcast"}

        # Splash's offer submission endpoint
        # Splash expects POST to the root of the submission URL
        submit_url = getattr(cfg, "SPLASH_SUBMIT_URL", "http://localhost:4000")
        url = submit_url.rstrip("/")
        payload = {"offer": offer_bech32}
        timeout = getattr(cfg, "SPLASH_POST_TIMEOUT", 15)
        retries = getattr(cfg, "SPLASH_POST_RETRIES", 2)
        retry_sleep = getattr(cfg, "SPLASH_POST_RETRY_SLEEP", 1.5)

        last_err = None
        for attempt in range(retries + 1):
            try:
                r = requests.post(
                    url, json=payload,
                    headers={"content-type": "application/json"},
                    timeout=timeout
                )

                if 200 <= r.status_code < 300:
                    # Mark as posted (lock-protected for thread safety)
                    with self._lock:
                        self._posted_fingerprints.add(fp)

                    # Reset health tracking on success
                    if not self._splash_healthy:
                        self._splash_healthy = True
                        self._consecutive_failures = 0
                        log_event("info", "splash_recovered",
                                  "Splash connection restored")

                    tid_short = trade_id[:16] + "..." if trade_id else "unknown"
                    log_event("debug", "splash_posted",
                              f"Broadcast to Splash OK (trade: {tid_short})")

                    return {"success": True, "trade_id": trade_id}

                last_err = f"HTTP {r.status_code}: {r.text[:200]}"

            except requests.Timeout:
                last_err = f"Timeout after {timeout}s"
            except requests.ConnectionError:
                last_err = "Connection refused — is Splash running?"
            except Exception as e:
                last_err = f"Unexpected error: {e}"

            # Retry with sleep
            if attempt < retries:
                time.sleep(retry_sleep)

        # All retries failed
        self._consecutive_failures += 1

        # Only log every Nth failure to avoid spamming
        if self._consecutive_failures <= 3 or self._consecutive_failures % self._max_silent_failures == 0:
            log_event("warning", "splash_post_failed",
                      f"Failed to broadcast to Splash "
                      f"(attempt {self._consecutive_failures}): {last_err}")

        if self._splash_healthy and self._consecutive_failures >= 3:
            self._splash_healthy = False
            log_event("warning", "splash_unhealthy",
                      "Splash appears offline — will keep trying silently")

        return {"success": False, "error": last_err}

    # -------------------------------------------------------------------
    # Repost active offers (recovery after outage)
    # -------------------------------------------------------------------

    def repost_active_offers(self, active_offers: List[Dict]):
        """Re-broadcast all active offers to Splash.

        Used after startup or Splash reconnect.

        Args:
            active_offers: List of offer dicts with 'trade_id' and 'offer_bech32'
        """
        count = 0
        for offer in active_offers:
            bech32 = offer.get("offer_bech32", "")
            trade_id = offer.get("trade_id", "")

            if bech32 and trade_id:
                self.queue_post(bech32, trade_id, force=True)
                count += 1

        if count > 0:
            log_event("info", "splash_repost_queued",
                      f"Queued {count} active offers for Splash rebroadcast")

    # -------------------------------------------------------------------
    # Health check
    # -------------------------------------------------------------------

    def check_health(self) -> Dict:
        """Quick health check — can we reach Splash?

        Returns: {healthy: bool, url: str, error: str|None}
        """
        submit_url = getattr(cfg, "SPLASH_SUBMIT_URL", "http://localhost:4000")
        try:
            # Just try connecting — Splash may not have a health endpoint,
            # so we just check if the port is open with a short timeout
            r = requests.get(submit_url, timeout=3)
            return {"healthy": True, "url": submit_url, "error": None}
        except requests.ConnectionError:
            return {"healthy": False, "url": submit_url,
                    "error": "Connection refused — Splash not running"}
        except Exception as e:
            return {"healthy": False, "url": submit_url, "error": str(e)}

    # -------------------------------------------------------------------
    # Stats & housekeeping
    # -------------------------------------------------------------------

    def get_stats(self) -> Dict:
        """Get broadcasting statistics."""
        return {
            "total_posted": self._total_posted,
            "total_failed": self._total_failed,
            "total_skipped": self._total_skipped,
            "queue_size": len(self._queue),
            "fingerprints_cached": len(self._posted_fingerprints),
            "healthy": self._splash_healthy,
            "consecutive_failures": self._consecutive_failures,
        }

    def reset_session_stats(self):
        """Reset per-run broadcast stats and dedup state."""
        with self._lock:
            self._queue = []
            self._posted_fingerprints.clear()
            self._total_posted = 0
            self._total_failed = 0
            self._total_skipped = 0
            self._splash_healthy = True
            self._consecutive_failures = 0

    def prune_fingerprints(self):
        """Periodically clear old fingerprints to prevent unbounded growth."""
        max_fps = 400
        if len(self._posted_fingerprints) > max_fps:
            old_len = len(self._posted_fingerprints)
            self._posted_fingerprints.clear()
            log_event("debug", "splash_fingerprints_cleared",
                      f"Cleared {old_len} fingerprints (exceeded {max_fps} cap)")

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------

    @staticmethod
    def _fingerprint(offer_bech32: str) -> str:
        """SHA256 fingerprint of offer bech32 string."""
        return hashlib.sha256(offer_bech32.strip().encode("utf-8")).hexdigest()
