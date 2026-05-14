#!/usr/bin/env python3
"""
bot.py — Lottery Sambad Scraper with Timing Window
====================================================
Timing windows (IST):
  1PM draw: scrape from 12:55 PM → 1:10 PM  (retry every 2 min)
  6PM draw: scrape from  5:55 PM → 6:10 PM  (retry every 2 min)
  8PM draw: scrape from  7:55 PM → 8:10 PM  (retry every 2 min)

Bot starts at window open, keeps retrying until:
  - Today's image found (SUCCESS → save and exit)
  - Window closes (GIVE UP → exit)

Usage:
  python bot.py --draw 1PM       # triggered by cron at 12:55 IST
  python bot.py --draw 6PM       # triggered by cron at 5:55 IST
  python bot.py --draw 8PM       # triggered by cron at 7:55 IST
  python bot.py --draw all       # backfill all 3 (no retry)
  python bot.py --draw 1PM --date 2026-05-10  # specific date, no retry
"""
import sys, re, json, time, logging, argparse, datetime, requests, shutil
from pathlib import Path
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("bot")

RESULTS_FILE = Path("results.json")
IMAGES_DIR   = Path("images")
MAX_HISTORY  = 90      # 3 draws × 30 days
RETRY_SECS   = 120     # retry every 2 minutes

# Draw timing windows (IST hours, minutes)
DRAW_WINDOWS = {
    "1PM": {"open": (12, 55), "close": (13, 10)},  # 12:55 PM → 1:10 PM IST
    "6PM": {"open": (17, 55), "close": (18, 10)},  # 5:55 PM  → 6:10 PM IST
    "8PM": {"open": (19, 55), "close": (20, 10)},  # 7:55 PM  → 8:10 PM IST
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer":         "https://www.google.com/",
    "Cache-Control":   "no-cache",
    "Pragma":          "no-cache",
}

SOURCE_PAGES = {
    "1PM": "https://lotterysambadresult.in/nagaland-state-lottery-sambad-today-result-1-pm.html",
    "6PM": "https://lotterysambadresult.in/nagaland-state-lottery-sambad-today-7-pm-result.html",
    "8PM": "https://lotterysambadresult.in/lottery-sambad-today-result-08-00-pm.html",
}

DRAW_ORDER = {"1PM": 1, "6PM": 2, "8PM": 3}

DRAW_NAMES = {
    "1PM": {0:"Dear Dwarka Morning",   1:"Dear Godavari Morning", 2:"Dear Indus Morning",
            3:"Dear Mahanadi Morning", 4:"Dear Meghna Morning",   5:"Dear Narmada Morning",
            6:"Dear Yamuna Morning"},
    "6PM": {0:"Dear Blitzen Evening",  1:"Dear Comet Evening",    2:"Dear Cupid Evening",
            3:"Dear Dancer Evening",   4:"Dear Dasher Evening",   5:"Dear Donner Evening",
            6:"Dear Vixen Evening"},
    "8PM": {0:"Dear Flamingo Evening", 1:"Dear Parrot Evening",   2:"Dear Eagle Evening",
            3:"Dear Falcon Evening",   4:"Dear Vulture Evening",  5:"Dear Ostrich Evening",
            6:"Dear Hawk Evening"},
}

# ── IST ───────────────────────────────────────────────────────────────────
def get_ist():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

def ist_date():
    return get_ist().strftime("%Y-%m-%d")

def ist_ts():
    return get_ist().strftime("%Y-%m-%dT%H:%M:%S+05:30")

def get_draw_name(draw, dt=None):
    if dt is None: dt = get_ist()
    return DRAW_NAMES.get(draw, {}).get(dt.weekday(), f"Dear {draw}")

def window_close_dt(draw):
    """Return today's window close time as IST datetime."""
    ist   = get_ist()
    h, m  = DRAW_WINDOWS[draw]["close"]
    return ist.replace(hour=h, minute=m, second=0, microsecond=0)

def past_window(draw):
    """True if current IST time is past the scraping window close."""
    return get_ist() >= window_close_dt(draw)

def seconds_until_close(draw):
    return max(0, int((window_close_dt(draw) - get_ist()).total_seconds()))

# ── Fetch ──────────────────────────────────────────────────────────────────
def fetch_page(url):
    """Fetch page with 3 attempts, adding cache-busting."""
    for attempt in range(1, 4):
        try:
            cb_url = f"{url}?cb={int(time.time())}"
            r = requests.get(cb_url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            log.info(f"  Fetch OK: {len(r.text):,} chars (attempt {attempt})")
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            log.warning(f"  Fetch attempt {attempt} failed: {e}")
            if attempt < 3:
                time.sleep(5)
    return None

# ── Image extraction ───────────────────────────────────────────────────────
def is_thumbnail(url):
    return bool(re.search(r"-\d{2,3}x\d{2,3}\.", url))

def date_in_text(text, ist_dt):
    """Check if a date string contains today's date in any common format."""
    months = ["january","february","march","april","may","june",
              "july","august","september","october","november","december"]
    t  = text.lower()
    d  = str(ist_dt.day)
    dz = str(ist_dt.day).zfill(2)
    mo = months[ist_dt.month - 1]
    yr = str(ist_dt.year)
    yr2 = yr[-2:]
    checks = [
        f"{d}-{mo}-{yr}", f"{dz}-{mo}-{yr}",
        f"{d} {mo} {yr}", f"{dz} {mo} {yr}",
        f"{mo}-{d}-{yr}", f"{mo} {d} {yr}",
        f"{dz}/{str(ist_dt.month).zfill(2)}/{yr}",
        f"{dz}/{str(ist_dt.month).zfill(2)}/{yr2}",
        f"{d}/{str(ist_dt.month)}/{yr}",
        # Also check numeric date in filename style
        f"{yr}{str(ist_dt.month).zfill(2)}{dz}",
    ]
    return any(c in t for c in checks)

def extract_image(soup, draw, ist_dt):
    """
    Extract image URL from page.
    Returns (url, is_today_confirmed) tuple.
    
    Strategies (in order):
    1. <figure class="aligncenter size-full"> img — confirmed pattern
    2. Any large wp-content image with today's date in alt/src
    3. Any large wp-content image with lottery keywords (best score)
    """
    # S1: confirmed figure pattern from real HTML
    fig = soup.find("figure", class_=lambda c: c and "aligncenter" in c and "size-full" in c)
    if fig:
        img = fig.find("img")
        if img:
            src = img.get("src", "").strip()
            alt = img.get("alt", "").strip()
            if src and "wp-content/uploads" in src and not is_thumbnail(src):
                today = date_in_text(alt + " " + src, ist_dt)
                log.info(f"  [S1] img found | today_confirmed={today}")
                log.info(f"       src: {src[:90]}")
                log.info(f"       alt: {alt[:70]}")
                return src, today

    # S2: scored scan of all wp-content images
    candidates = []
    for img in soup.find_all("img", src=True):
        src = img.get("src", "")
        alt = img.get("alt", "").lower()
        if "wp-content/uploads" not in src: continue
        if is_thumbnail(src): continue
        if any(x in src.lower() for x in ["logo","banner","favicon","icon","header","ad-"]): continue

        score = 0
        combined = alt + " " + src.lower()
        if any(k in combined for k in ["sambad","result","lottery","dear","nagaland"]): score += 4
        if draw.replace("PM","") in combined: score += 3
        if date_in_text(combined, ist_dt): score += 10   # strong signal
        if src.endswith((".webp",".jpg",".jpeg",".png")): score += 1
        # Prefer larger images (full result images are large files)
        if not is_thumbnail(src): score += 2

        if score > 0:
            is_today = date_in_text(combined, ist_dt)
            candidates.append((score, src, is_today))

    if candidates:
        candidates.sort(reverse=True)
        best_score, best_src, best_today = candidates[0]
        log.info(f"  [S2] Best score={best_score} today={best_today}")
        log.info(f"       src: {best_src[:90]}")
        return best_src, best_today

    log.warning("  No image found on page")
    return None, False

def extract_pdf(soup):
    """Extract PDF download link."""
    # Confirmed class from real HTML
    dl = soup.find("a", class_=lambda c: c and "download_btn" in c)
    if dl:
        href = dl.get("href", "")
        if href and ".pdf" in href.lower():
            return href
    # Fallback
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf") and "wp-content" in href:
            return href
    return None

# ── Image download ─────────────────────────────────────────────────────────
def download_image(img_url, draw, date):
    """Download image to local images/ folder."""
    IMAGES_DIR.mkdir(exist_ok=True)
    ext  = "webp" if img_url.lower().endswith(".webp") else "jpg"
    name = f"nagaland-{draw.lower()}-{date}.{ext}"
    path = IMAGES_DIR / name

    if path.exists() and path.stat().st_size > 5000:
        log.info(f"  Already downloaded: {name}")
        return name

    try:
        hdrs = {**HEADERS, "Referer": "https://lotterysambadresult.in/"}
        r = requests.get(img_url, headers=hdrs, timeout=30, stream=True)
        r.raise_for_status()
        with open(path, "wb") as f:
            shutil.copyfileobj(r.raw, f)
        kb = path.stat().st_size // 1024
        log.info(f"  Downloaded: {name} ({kb} KB)")
        return name
    except Exception as e:
        log.warning(f"  Download failed: {e} — will store URL directly")
        if path.exists():
            path.unlink()
        return None

# ── JSON ───────────────────────────────────────────────────────────────────
def load_results():
    if RESULTS_FILE.exists():
        try:
            d = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
            log.info(f"Loaded results.json: {len(d.get('nagaland',[]))} records")
            return d
        except Exception as e:
            log.error(f"Load error: {e}")
    return {"nagaland": [], "kerala": [], "last_updated": "", "total_records": 0}

def save_results(data):
    tmp = RESULTS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(RESULTS_FILE)
    log.info(f"Saved results.json ({RESULTS_FILE.stat().st_size:,} bytes)")

def upsert_record(nagaland, record, date, draw):
    """Insert new or update existing record for date+draw."""
    existing = next((r for r in nagaland if r.get("date")==date and r.get("draw")==draw), None)
    if existing:
        changed = False
        if existing.get("image") != record["image"]:
            existing["image"] = record["image"]; changed = True
        if record.get("pdf") and existing.get("pdf") != record["pdf"]:
            existing["pdf"] = record["pdf"]; changed = True
        if changed:
            existing["fetched_at"] = record["fetched_at"]
            existing.pop("seeded", None)
            log.info(f"  Updated existing record: {date} {draw}")
        return changed
    else:
        nagaland.append(record)
        nagaland.sort(
            key=lambda x: (x["date"], DRAW_ORDER.get(x["draw"], 0)),
            reverse=True
        )
        del nagaland[MAX_HISTORY:]
        log.info(f"  New record added: {date} {draw} | {record['draw_name']}")
        return True

# ── Main draw scraper with timing window ──────────────────────────────────
def scrape_draw(draw, date, results, use_window=True):
    """
    Scrape a single draw with timing window retry.
    
    use_window=True:  retry every 2 min until window closes (for daily cron)
    use_window=False: single attempt only (for backfill/manual)
    """
    log.info(f"\n{'━'*55}")
    log.info(f"DRAW: {draw} | DATE: {date} | WINDOW: {use_window}")
    if use_window:
        wc = window_close_dt(draw)
        log.info(f"Window closes at: {wc.strftime('%I:%M %p')} IST")
    log.info(f"{'━'*55}")

    # Check if already have a good record
    nagaland = results.setdefault("nagaland", [])
    existing = next((r for r in nagaland if r.get("date")==date and r.get("draw")==draw), None)
    if existing and existing.get("image") and not existing.get("seeded"):
        log.info(f"Already have image for {date} {draw} — skipping")
        return False

    try:
        ist_dt = datetime.datetime.strptime(date, "%Y-%m-%d")
    except:
        ist_dt = get_ist()

    is_today = (date == ist_date())
    attempt  = 0

    while True:
        attempt += 1
        ist_now = get_ist()
        log.info(f"\nAttempt #{attempt} | IST: {ist_now.strftime('%I:%M:%S %p')}")

        soup = fetch_page(SOURCE_PAGES[draw])
        if soup:
            img_url, today_confirmed = extract_image(soup, draw, ist_dt)
            pdf_url = extract_pdf(soup) if soup else None

            if img_url:
                # For today's draw via window: require today's image
                # For backfill/manual: accept any image
                if not use_window or not is_today or today_confirmed:
                    log.info(f"  ✅ Image found! today_confirmed={today_confirmed}")
                    
                    # Download locally
                    local = download_image(img_url, draw, date)
                    image_store = f"images/{local}" if local else img_url

                    record = {
                        "date":       date,
                        "draw":       draw,
                        "draw_name":  get_draw_name(draw, ist_dt),
                        "image":      image_store,
                        "pdf":        pdf_url or "",
                        "source":     "official",
                        "verified":   True,
                        "fetched_at": ist_ts(),
                    }
                    return upsert_record(nagaland, record, date, draw)
                else:
                    log.warning(f"  ⚠️  Image found but NOT today's date — will retry")
            else:
                log.warning(f"  ❌ No image found on page")
        else:
            log.warning(f"  ❌ Page fetch failed")

        # Decide whether to retry
        if not use_window:
            log.info(f"  Single-attempt mode — done")
            return False

        if past_window(draw):
            log.warning(f"  ⏰ Window closed — giving up")
            return False

        secs = seconds_until_close(draw)
        wait = min(RETRY_SECS, secs)
        if wait <= 10:
            log.warning(f"  Window closing soon ({secs}s left) — final attempt exhausted")
            return False

        log.info(f"  ⏳ Waiting {wait}s before retry ({secs}s until window close)…")
        time.sleep(wait)

# ── Main ───────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="Lottery Sambad Scraper with Timing Window")
    p.add_argument("--draw", default=None,
                   help="Which draw: 1PM / 6PM / 8PM / all")
    p.add_argument("--date", default=None,
                   help="Date YYYY-MM-DD (default: today IST). Forces no-window mode.")
    p.add_argument("--no-window", action="store_true",
                   help="Disable timing window — single attempt only")
    args = p.parse_args()

    date = args.date or ist_date()

    # If specific date given or --no-window → no retry window
    use_window = (args.date is None) and (not args.no_window)

    if args.draw == "all":
        draws      = ["1PM", "6PM", "8PM"]
        use_window = False  # backfill mode — no window
    elif args.draw in ("1PM", "6PM", "8PM"):
        draws = [args.draw]
    else:
        # Auto-detect from IST time
        h = get_ist().hour
        draws = ["1PM" if h < 13 else "6PM" if h < 18 else "8PM"]

    log.info("=" * 60)
    log.info(f"bot.py | IST: {ist_ts()}")
    log.info(f"Date: {date} | Draws: {draws} | Window: {use_window}")
    log.info("=" * 60)

    results     = load_results()
    any_changed = False

    for draw in draws:
        try:
            if scrape_draw(draw, date, results, use_window=use_window):
                any_changed = True
        except KeyboardInterrupt:
            log.warning("Interrupted — saving current state")
            break
        except Exception as e:
            log.error(f"Error on {draw}: {e}")
        if len(draws) > 1:
            time.sleep(3)

    results["last_updated"]  = ist_ts()
    results["total_records"] = len(results.get("nagaland", []))
    save_results(results)

    log.info("\n" + "=" * 60)
    log.info("SUMMARY:")
    for r in results.get("nagaland", [])[:9]:
        s = " [seed]" if r.get("seeded") else ""
        log.info(f"  {'✅' if r.get('image') else '❌'} {r['date']} {r['draw']:3} | {r['draw_name']}{s}")
    log.info(f"Changed={any_changed} | Total={results['total_records']}")
    log.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
