#!/usr/bin/env python3
"""
bot.py — Lottery Result Automation Bot
========================================
Main orchestrator. Fetches PDF results from official sources,
stores them locally, updates results.json (with history preserved),
and prints a summary.

Usage:
    python bot.py                    # auto-detect draw from IST clock
    python bot.py --draw 8PM         # force specific draw
    python bot.py --state nagaland   # run single state only

GitHub Actions calls this script 3× daily.

Author : Lottery Bot
Version: 2.0.0
"""

import sys
import json
import logging
import argparse
import datetime
from pathlib import Path

from scraper import get_nagaland_result, get_kerala_result, get_ist_now
from parser  import build_record

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("bot")

# ── Config ────────────────────────────────────────────────────────────
RESULTS_FILE    = Path("results.json")
MAX_HISTORY     = 30        # keep last N entries per state/draw combo
STATES_ENABLED  = ["nagaland", "kerala"]   # add more here later


# ── results.json helpers ──────────────────────────────────────────────

def load_results() -> dict:
    """Load existing results.json or return a fresh skeleton."""
    if RESULTS_FILE.exists():
        try:
            with open(RESULTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            log.info(f"Loaded existing results.json")
            return data
        except (json.JSONDecodeError, OSError) as e:
            log.error(f"Corrupted results.json: {e} — starting fresh")

    return {
        "nagaland": [],
        "kerala": [],
        "last_updated": "",
        "total_records": 0,
    }


def save_results(data: dict) -> None:
    """Write results.json atomically (write to tmp then rename)."""
    tmp = RESULTS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(RESULTS_FILE)
    log.info(f"✓ results.json saved ({RESULTS_FILE.stat().st_size} bytes)")


def is_duplicate(existing_list: list, new_record: dict) -> bool:
    """
    Return True if a record for the same date+draw already exists.
    This prevents double-posting the same result.
    """
    for rec in existing_list:
        if rec.get("date") == new_record["date"] and \
           rec.get("draw") == new_record["draw"]:
            log.info(
                f"Duplicate found: {new_record['date']} {new_record['draw']} "
                f"— skipping"
            )
            return True
    return False


def insert_record(existing_list: list, new_record: dict) -> list:
    """
    Prepend new_record at the front (newest first).
    Trim history to MAX_HISTORY entries.
    """
    updated = [new_record] + existing_list
    if len(updated) > MAX_HISTORY:
        trimmed = len(updated) - MAX_HISTORY
        log.info(f"Trimming {trimmed} old records (keeping {MAX_HISTORY})")
        updated = updated[:MAX_HISTORY]
    return updated


def count_total(data: dict) -> int:
    """Count total records across all states."""
    total = 0
    for key in STATES_ENABLED:
        total += len(data.get(key, []))
    return total


# ── Fetch helpers ─────────────────────────────────────────────────────

def run_nagaland(draw: str, date_str: str, results: dict) -> bool:
    """Fetch and store Nagaland result. Returns True if new data added."""
    log.info(f"── Nagaland {draw} ──")
    raw = get_nagaland_result(draw)
    if not raw:
        log.warning(f"Nagaland {draw}: No data from any source")
        return False

    record = build_record("nagaland", raw, date_str)
    if not record:
        log.warning(f"Nagaland {draw}: Record build failed")
        return False

    state_list = results.setdefault("nagaland", [])
    if is_duplicate(state_list, record):
        return False

    results["nagaland"] = insert_record(state_list, record)
    log.info(
        f"✓ Nagaland {draw} added: pdf={record['pdf']} "
        f"image={record['image'] or 'N/A'}"
    )
    return True


def run_kerala(draw: str, date_str: str, results: dict) -> bool:
    """Fetch and store Kerala result. Returns True if new data added."""
    # Kerala has a single draw per day (3PM or 4PM depending on lottery)
    kerala_draw = "3PM"
    log.info(f"── Kerala {kerala_draw} ──")
    raw = get_kerala_result(kerala_draw)
    if not raw:
        log.warning(f"Kerala {kerala_draw}: No data from any source")
        return False

    record = build_record("kerala", raw, date_str)
    if not record:
        log.warning(f"Kerala {kerala_draw}: Record build failed")
        return False

    state_list = results.setdefault("kerala", [])
    if is_duplicate(state_list, record):
        return False

    results["kerala"] = insert_record(state_list, record)
    log.info(
        f"✓ Kerala {kerala_draw} added: pdf={record['pdf']} "
        f"image={record['image'] or 'N/A'}"
    )
    return True


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Lottery Result Bot")
    parser.add_argument(
        "--draw",
        choices=["1PM", "6PM", "8PM", "3PM"],
        default=None,
        help="Force a specific draw time (default: auto from IST clock)",
    )
    parser.add_argument(
        "--state",
        choices=STATES_ENABLED + ["all"],
        default="all",
        help="Run for a specific state only (default: all)",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Override date (YYYY-MM-DD). Default: today IST",
    )
    args = parser.parse_args()

    # Determine date
    if args.date:
        date_str = args.date
    else:
        date_str = (get_ist_now()).strftime("%Y-%m-%d")

    # Determine draw
    if args.draw:
        draw = args.draw
    else:
        from scraper import detect_draw_from_time
        draw = detect_draw_from_time()

    log.info("=" * 60)
    log.info(f" Lottery Bot v2.0 | Date: {date_str} | Draw: {draw}")
    log.info(f" States: {args.state}")
    log.info("=" * 60)

    # Load existing results
    results = load_results()

    # Track whether any new data was added
    any_updated = False

    states_to_run = STATES_ENABLED if args.state == "all" else [args.state]

    for state in states_to_run:
        if state == "nagaland":
            updated = run_nagaland(draw, date_str, results)
        elif state == "kerala":
            updated = run_kerala(draw, date_str, results)
        else:
            log.warning(f"Unknown state: {state}")
            continue

        if updated:
            any_updated = True

    # Update metadata
    ist_now = get_ist_now()
    results["last_updated"] = ist_now.strftime("%Y-%m-%dT%H:%M:%S+05:30")
    results["total_records"] = count_total(results)

    # Always save (metadata timestamp updates even if no new records)
    save_results(results)

    # Summary
    log.info("=" * 60)
    if any_updated:
        log.info("✅ SUCCESS: New results saved")
        # Print JSON summary for GitHub Actions log
        for state in states_to_run:
            entries = results.get(state, [])
            if entries:
                latest = entries[0]
                log.info(
                    f"  {state.upper()} latest → "
                    f"{latest['date']} {latest['draw']} | "
                    f"PDF: {bool(latest.get('pdf'))} | "
                    f"Image: {bool(latest.get('image'))}"
                )
    else:
        log.info("ℹ️  No new results — database already up to date")

    log.info(f"Total records in DB: {results['total_records']}")
    log.info("=" * 60)

    # Exit code: 0 = success (GitHub Actions uses this)
    sys.exit(0)


if __name__ == "__main__":
    main()
