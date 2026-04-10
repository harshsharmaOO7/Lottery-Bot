#!/usr/bin/env python3
"""
bot.py — Lottery Result Bot (Simplified Image-Only System)
===========================================================
Kya karta hai:
  1. lotterysambadresult.in se aaj ki result IMAGE URL scrape karta hai
  2. results.json mein save karta hai (history keep karta hai)
  3. Koi PDF download nahi, koi pdf2image nahi

Kyun simplified:
  Source sites sirf images upload karti hain, PDF nahi hota.
  Isliye directly image URL store karo aur frontend pe dikhao.

Usage:
  python bot.py              # IST time se draw auto-detect
  python bot.py --draw 8PM   # Force specific draw
  python bot.py --draw all   # Sare draws ek saath
  python bot.py --date 2026-04-11  # Manual date
"""

import sys
import json
import time
import logging
import argparse
import datetime
import requests
from pathlib import Path
from bs4 import BeautifulSoup

# ── Logging setup ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("bot")

# ── Config ────────────────────────────────────────────────────────────
RESULTS_FILE = Path("results.json")
MAX_HISTORY  = 30   # Kitne purane results rakhe

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
    "Referer": "https://www.google.com/",
    "Cache-Control": "no-cache",
}

# ── Source URLs (confirmed from HTML analysis) ────────────────────────
SOURCE_PAGES = {
    "1PM": "https://lotterysambadresult.in/nagaland-state-lottery-sambad-today-result-1-pm.html",
    "6PM": "https://lotterysambadresult.in/nagaland-state-lottery-sambad-today-7-pm-result.html",
    "8PM": "https://lotterysambadresult.in/lottery-sambad-today-result-08-00-pm.html",
}

# Draw name schedules (official Nagaland)
DRAW_NAMES = {
    "1PM": {0:"Dear Dwarka Morning",   1:"Dear Godavari Morning", 2:"Dear Indus Morning",
            3:"Dear Mahanadi Morning", 4:"Dear Meghna Morning",   5:"Dear Narmada Morning",
            6:"Dear Yamuna Morning"},
    "6PM": {0:"Dear Blitzen Evening",  1:"Dear Comet Evening",   2:"Dear Cupid Evening",
            3:"Dear Dancer Evening",   4:"Dear Dasher Evening",  5:"Dear Donner Evening",
            6:"Dear Vixen Evening"},
    "8PM": {0:"Dear Finch Night",      1:"Dear Goose Night",     2:"Dear Pelican Night",
            3:"Dear Sandpiper Night",  4:"Dear SeaGull Night",   5:"Dear Stork Night",
            6:"Dear Toucan Night"},
}


# ── IST helpers ───────────────────────────────────────────────────────

def get_ist() -> datetime.datetime:
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

def ist_date() -> str:
    return get_ist().strftime("%Y-%m-%d")

def ist_ts() -> str:
    return get_ist().strftime("%Y-%m-%dT%H:%M:%S+05:30")

def auto_draw() -> str:
    h = get_ist().hour
    if h < 13:      return "1PM"
    elif h < 18:    return "6PM"
    else:           return "8PM"

def draw_name(draw: str) -> str:
    dow = get_ist().weekday()  # 0=Mon, 6=Sun
    return DRAW_NAMES.get(draw, {}).get(dow, f"Dear {draw}")


# ── Image scraper ─────────────────────────────────────────────────────

def fetch_image_url(draw: str) -> str | None:
    """
    lotterysambadresult.in se aaj ki result image URL nikalo.

    HTML pattern (confirmed):
    <figure class="aligncenter size-full">
      <img src="...wp-content/uploads/2026/04/img_HASH.webp"
           alt="dear-lottery-sambad-8-pm-8-April-2026-winner-list"
           fetchpriority="high">
    </figure>
    """
    url = SOURCE_PAGES.get(draw)
    if not url:
        log.error(f"Unknown draw: {draw}")
        return None

    log.info(f"Fetching {draw} page: {url}")

    for attempt in range(1, 4):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            log.info(f"Page loaded (attempt {attempt}): {len(r.text)} chars")
            break
        except requests.exceptions.HTTPError as e:
            log.warning(f"HTTP {e.response.status_code} — attempt {attempt}/3")
            if attempt == 3: return None
            time.sleep(3 * attempt)
        except Exception as e:
            log.warning(f"Error: {e} — attempt {attempt}/3")
            if attempt == 3: return None
            time.sleep(3 * attempt)

    soup = BeautifulSoup(r.text, "html.parser")

    # ── Strategy 1: <figure class="aligncenter size-full"> img ──
    fig = soup.find(
        "figure",
        class_=lambda c: c and "aligncenter" in c and "size-full" in c
    )
    if fig:
        img = fig.find("img")
        if img:
            src = img.get("src", "").strip()
            alt = img.get("alt", "").strip()
            log.info(f"Strategy 1 — figure img found")
            log.info(f"  src: {src}")
            log.info(f"  alt: {alt}")
            if src and "wp-content/uploads" in src:
                # Verify it's today's image via alt text date
                ist = get_ist()
                months = ["January","February","March","April","May","June",
                          "July","August","September","October","November","December"]
                today_pattern = f"{ist.day}-{months[ist.month-1]}-{ist.year}"
                if today_pattern.lower() in alt.lower():
                    log.info(f"  ✓ Date verified in alt: '{today_pattern}'")
                    return src
                else:
                    log.warning(f"  Date mismatch: expected '{today_pattern}' in alt '{alt}'")
                    log.info("  Returning anyway (most recent image)")
                    return src

    # ── Strategy 2: fetchpriority="high" img with wp-content ──
    log.info("Strategy 2 — fetchpriority=high img...")
    for img in soup.find_all("img", attrs={"fetchpriority": "high"}):
        src = img.get("src", "")
        if "wp-content/uploads" in src and not _is_thumbnail(src):
            alt = img.get("alt", "")
            if any(kw in alt.lower() for kw in ["sambad","lottery","dear","result"]):
                log.info(f"  Found: {src}")
                return src

    # ── Strategy 3: og:image meta ──
    log.info("Strategy 3 — og:image meta...")
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        src = og["content"]
        if "wp-content/uploads" in src:
            log.info(f"  Found: {src}")
            return src

    # ── Strategy 4: Any large wp-content image ──
    log.info("Strategy 4 — any wp-content image...")
    candidates = []
    for img in soup.find_all("img", src=True):
        src = img.get("src", "")
        if "wp-content/uploads" not in src: continue
        if _is_thumbnail(src): continue
        if any(x in src.lower() for x in ["logo","icon","avatar","banner"]): continue
        alt = img.get("alt","").lower()
        score = 0
        if any(kw in alt for kw in ["sambad","lottery","result","dear","winner"]): score += 5
        if any(ext in src.lower() for ext in [".webp",".jpg",".jpeg"]): score += 2
        candidates.append((score, src))

    if candidates:
        candidates.sort(reverse=True)
        best = candidates[0][1]
        log.info(f"  Best candidate (score={candidates[0][0]}): {best}")
        return best

    log.warning(f"No image found for {draw} draw!")
    return None


def _is_thumbnail(src: str) -> bool:
    """Check if URL is a small thumbnail like -150x150."""
    import re
    return bool(re.search(r"-\d{2,3}x\d{2,3}\.", src))


# ── results.json helpers ──────────────────────────────────────────────

def load_results() -> dict:
    if RESULTS_FILE.exists():
        try:
            data = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
            log.info(f"Loaded results.json: {data.get('total_records', 0)} records")
            return data
        except Exception as e:
            log.error(f"results.json corrupted: {e}")
    return {"nagaland": [], "kerala": [], "last_updated": "", "total_records": 0}


def save_results(data: dict):
    tmp = RESULTS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(RESULTS_FILE)
    log.info(f"✓ results.json saved ({RESULTS_FILE.stat().st_size} bytes)")


def is_duplicate(arr: list, date: str, draw: str) -> bool:
    for r in arr:
        if r.get("date") == date and r.get("draw") == draw:
            return True
    return False


def update_existing(arr: list, date: str, draw: str, image: str) -> bool:
    """If record for same date+draw exists, update the image URL."""
    for r in arr:
        if r.get("date") == date and r.get("draw") == draw:
            if r.get("image") != image:
                r["image"] = image
                r["fetched_at"] = ist_ts()
                log.info(f"Updated existing record image: {date} {draw}")
                return True
            else:
                log.info(f"Image unchanged for {date} {draw} — no update needed")
                return False
    return False


# ── Main runner ───────────────────────────────────────────────────────

def run_draw(draw: str, date: str, results: dict) -> bool:
    """Fetch one draw's result and update results.json. Returns True if changed."""
    log.info(f"━━━━ {draw} ━━━━")

    img_url = fetch_image_url(draw)
    if not img_url:
        log.warning(f"No image URL for {draw} — skipping")
        return False

    nagaland = results.setdefault("nagaland", [])

    # If record for today exists, try to update image
    if is_duplicate(nagaland, date, draw):
        return update_existing(nagaland, date, draw, img_url)

    # New record
    record = {
        "date":       date,
        "draw":       draw,
        "draw_name":  draw_name(draw),
        "image":      img_url,
        "pdf":        "",          # No PDF from these sources
        "source":     SOURCE_PAGES.get(draw, ""),
        "verified":   True,
        "fetched_at": ist_ts(),
    }

    # Prepend (newest first) + trim history
    nagaland.insert(0, record)
    if len(nagaland) > MAX_HISTORY:
        nagaland[:] = nagaland[:MAX_HISTORY]

    log.info(f"✓ Added: {date} {draw} | {draw_name(draw)}")
    log.info(f"  Image: {img_url}")
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--draw", default=None,
                   help="1PM / 6PM / 8PM / all (default: auto from IST time)")
    p.add_argument("--date", default=None, help="YYYY-MM-DD (default: today IST)")
    args = p.parse_args()

    date = args.date or ist_date()
    draws_to_run = []

    if args.draw == "all":
        draws_to_run = ["1PM", "6PM", "8PM"]
    elif args.draw in ("1PM","6PM","8PM"):
        draws_to_run = [args.draw]
    else:
        draws_to_run = [auto_draw()]

    log.info("=" * 56)
    log.info(f"  Lottery Bot | IST Date: {date} | Draws: {draws_to_run}")
    log.info("=" * 56)

    results     = load_results()
    any_changed = False

    for draw in draws_to_run:
        changed = run_draw(draw, date, results)
        if changed:
            any_changed = True
        time.sleep(2)  # Polite delay between requests

    # Always update metadata
    results["last_updated"]  = ist_ts()
    results["total_records"] = sum(
        len(results.get(s, [])) for s in ["nagaland", "kerala"]
    )
    save_results(results)

    log.info("=" * 56)
    if any_changed:
        log.info("✅ Results updated successfully!")
        for r in results.get("nagaland", [])[:3]:
            log.info(f"   {r['date']} {r['draw']} — {r['draw_name']}")
            log.info(f"   Image: {r.get('image','N/A')[:70]}")
    else:
        log.info("ℹ️  No changes — results already up to date")
    log.info(f"  Total: {results['total_records']} records")
    log.info("=" * 56)

    sys.exit(0)


if __name__ == "__main__":
    main()
