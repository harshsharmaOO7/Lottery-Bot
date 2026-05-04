#!/usr/bin/env python3
"""
bot.py v4 — Lottery Sambad Daily Scraper
==========================================
Key features:
  - Retries scraping until TODAY's image is found (max 2 hours, every 5 min)
  - Downloads image locally to images/ folder
  - Stores full https:// URL as fallback if download fails
  - MAX_HISTORY = 90
  - No prefilled / hardcoded data — pure scrape only

Run modes:
  python bot.py                      → auto-detect draw from IST time, retry until found
  python bot.py --draw 1PM           → specific draw, retry until found
  python bot.py --draw all           → all 3 draws (backfill mode, no retry)
  python bot.py --draw all --date 2026-04-29  → specific date, no retry
  python bot.py --draw 1PM --no-retry → single attempt, no retry loop
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

RESULTS_FILE  = Path("results.json")
IMAGES_DIR    = Path("images")
MAX_HISTORY   = 90        # 3 draws × 30 days
RETRY_EVERY   = 300       # 5 minutes between retries
MAX_WAIT_SEC  = 7200      # 2 hours max wait (after that, give up)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.google.com/",
    "Cache-Control": "no-cache",
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

# ── IST helpers ────────────────────────────────────────────────────────────
def get_ist():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

def ist_date():
    return get_ist().strftime("%Y-%m-%d")

def ist_ts():
    return get_ist().strftime("%Y-%m-%dT%H:%M:%S+05:30")

def auto_draw():
    h = get_ist().hour
    return "1PM" if h < 13 else "6PM" if h < 18 else "8PM"

def get_draw_name(draw, dt=None):
    if dt is None:
        dt = get_ist()
    return DRAW_NAMES.get(draw, {}).get(dt.weekday(), f"Dear {draw}")

# ── Page fetch ─────────────────────────────────────────────────────────────
def fetch_page(url):
    for attempt in range(1, 4):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            log.info(f"Fetched {len(r.text):,} chars from {url[:60]}")
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            log.warning(f"Fetch attempt {attempt} failed: {e}")
            time.sleep(5 * attempt)
    return None

# ── Image extraction ───────────────────────────────────────────────────────
def is_thumbnail(url):
    return bool(re.search(r"-\d{2,3}x\d{2,3}\.", url))

def date_in_alt(alt, ist_dt):
    """Check if the image alt text contains today's date in any common format."""
    months = ["january","february","march","april","may","june",
              "july","august","september","october","november","december"]
    alt_l  = alt.lower()
    day    = str(ist_dt.day)
    dayz   = str(ist_dt.day).zfill(2)
    mon    = months[ist_dt.month - 1]
    yr     = str(ist_dt.year)
    yr2    = yr[-2:]
    patterns = [
        f"{day}-{mon}-{yr}", f"{dayz}-{mon}-{yr}",
        f"{mon}-{day}-{yr}", f"{mon} {day} {yr}",
        f"{day} {mon} {yr}", f"{dayz}/{str(ist_dt.month).zfill(2)}/{yr}",
        f"{dayz}/{str(ist_dt.month).zfill(2)}/{yr2}",
        f"{day}/{str(ist_dt.month)}/{yr}",
    ]
    return any(p in alt_l for p in patterns)

def extract_image(soup, draw, ist_dt):
    """
    Extract result image URL from page.
    Returns (url, is_todays_image) tuple.
    """
    # Strategy 1: confirmed <figure class="aligncenter size-full"> pattern
    fig = soup.find("figure", class_=lambda c: c and "aligncenter" in c and "size-full" in c)
    if fig:
        img = fig.find("img")
        if img:
            src = img.get("src", "").strip()
            alt = img.get("alt", "").strip()
            if src and "wp-content/uploads" in src and not is_thumbnail(src):
                is_today = date_in_alt(alt, ist_dt)
                log.info(f"[S1] Found image | today={is_today} | alt: {alt[:60]}")
                return src, is_today

    # Strategy 2: scored scan
    draw_num = draw.replace("PM", "")
    candidates = []
    for img in soup.find_all("img", src=True):
        src = img.get("src", "")
        alt = img.get("alt", "").lower()
        if "wp-content/uploads" not in src:
            continue
        if is_thumbnail(src):
            continue
        if any(x in src.lower() for x in ["logo", "banner", "favicon", "icon", "sponsor"]):
            continue
        score = 0
        if any(k in alt for k in ["sambad", "result", "lottery", "dear", "nagaland"]):
            score += 4
        if draw_num in alt:
            score += 3
        if date_in_alt(alt, ist_dt):
            score += 8
        if src.endswith((".webp", ".jpg", ".jpeg")):
            score += 1
        if score > 0:
            candidates.append((score, src, date_in_alt(alt, ist_dt)))

    if candidates:
        candidates.sort(reverse=True)
        best_score, best_src, best_is_today = candidates[0]
        log.info(f"[S2] Best (score={best_score}, today={best_is_today}): {best_src[:80]}")
        return best_src, best_is_today

    return None, False

def extract_pdf(soup):
    dl = soup.find("a", class_=lambda c: c and "download_btn" in c)
    if dl:
        href = dl.get("href", "")
        if href and ".pdf" in href.lower():
            return href
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf") and "wp-content" in href:
            return href
    return None

# ── Image download ─────────────────────────────────────────────────────────
def download_image(img_url, draw, date):
    """Download image to local images/ folder. Returns local path or None."""
    IMAGES_DIR.mkdir(exist_ok=True)
    ext        = "webp" if img_url.lower().endswith(".webp") else "jpg"
    local_name = f"nagaland-{draw.lower()}-{date}.{ext}"
    local_path = IMAGES_DIR / local_name

    if local_path.exists() and local_path.stat().st_size > 10000:
        log.info(f"Already downloaded: {local_name}")
        return local_name

    try:
        img_headers = {**HEADERS, "Referer": "https://lotterysambadresult.in/"}
        r = requests.get(img_url, headers=img_headers, timeout=30, stream=True)
        r.raise_for_status()
        with open(local_path, "wb") as f:
            shutil.copyfileobj(r.raw, f)
        size_kb = local_path.stat().st_size // 1024
        log.info(f"Downloaded: {local_name} ({size_kb} KB)")
        return local_name
    except Exception as e:
        log.warning(f"Download failed — will store URL: {e}")
        if local_path.exists():
            local_path.unlink()
        return None

# ── JSON I/O ───────────────────────────────────────────────────────────────
def load_results():
    if RESULTS_FILE.exists():
        try:
            data = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
            log.info(f"Loaded results.json — {len(data.get('nagaland', []))} records")
            return data
        except Exception as e:
            log.error(f"results.json error: {e}")
    return {"nagaland": [], "kerala": [], "last_updated": "", "total_records": 0}

def save_results(data):
    tmp = RESULTS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(RESULTS_FILE)
    log.info(f"✓ Saved results.json ({RESULTS_FILE.stat().st_size:,} bytes)")

# ── Single scrape attempt ─────────────────────────────────────────────────
def scrape_once(draw, date, ist_dt, need_today):
    """
    Try to scrape draw result once.
    Returns: (image_url, is_todays, pdf_url) or (None, False, None) on failure.
    """
    soup = fetch_page(SOURCE_PAGES[draw])
    if not soup:
        return None, False, None

    img_url, is_today = extract_image(soup, draw, ist_dt)
    pdf_url = extract_pdf(soup)

    if not img_url:
        log.warning(f"No image found on page for {draw}")
        return None, False, None

    if need_today and not is_today:
        log.warning(f"Image found but NOT today's ({date}) — will retry")
        return None, False, None

    return img_url, is_today, pdf_url

# ── Draw runner with retry ─────────────────────────────────────────────────
def run_draw(draw, date, results, retry=True):
    """
    Scrape a draw result. If retry=True, keeps retrying until today's image found.
    Returns True if a record was added/updated, False otherwise.
    """
    log.info(f"{'='*20} {draw} | {date} {'='*20}")

    try:
        ist_dt = datetime.datetime.strptime(date, "%Y-%m-%d")
    except Exception:
        ist_dt = get_ist()

    # If today is the target date, we need today's image
    need_today = (date == ist_date())

    # Check if already have today's result (skip retry if so)
    nagaland = results.setdefault("nagaland", [])
    existing = next((r for r in nagaland if r.get("date") == date and r.get("draw") == draw), None)
    if existing and existing.get("image") and not existing.get("seeded"):
        log.info(f"Already have {date} {draw} — skipping")
        return False

    # ── Retry loop ────────────────────────────────────────────────
    start_time = time.time()
    attempt    = 0

    while True:
        attempt += 1
        elapsed = int(time.time() - start_time)

        log.info(f"Attempt #{attempt} | elapsed: {elapsed}s")
        img_url, is_today, pdf_url = scrape_once(draw, date, ist_dt, need_today)

        if img_url:
            break  # Got a valid image

        if not retry or not need_today:
            log.warning(f"No image for {draw} {date} — giving up (retry={retry})")
            return False

        if elapsed >= MAX_WAIT_SEC:
            log.error(f"Max wait {MAX_WAIT_SEC}s reached for {draw} {date} — giving up")
            return False

        wait = min(RETRY_EVERY, MAX_WAIT_SEC - elapsed)
        log.info(f"Waiting {wait}s before next attempt… (max wait: {MAX_WAIT_SEC}s)")
        time.sleep(wait)

    # ── Got image — download locally ──────────────────────────────
    local_name = download_image(img_url, draw, date)

    # Prefer local path, fallback to external URL
    image_store = f"images/{local_name}" if local_name else img_url

    # ── Update or insert record ───────────────────────────────────
    if existing:
        changed = False
        if existing.get("image") != image_store:
            existing["image"] = image_store
            changed = True
        if pdf_url and existing.get("pdf") != pdf_url:
            existing["pdf"] = pdf_url
            changed = True
        if changed:
            existing["fetched_at"] = ist_ts()
            existing.pop("seeded", None)
            log.info(f"✓ Updated existing: {date} {draw}")
        else:
            log.info("Record unchanged")
        return changed

    record = {
        "date":       date,
        "draw":       draw,
        "draw_name":  get_draw_name(draw, ist_dt),
        "image":      image_store,
        "pdf":        pdf_url or "",
        "source":     SOURCE_PAGES[draw],
        "verified":   True,
        "fetched_at": ist_ts(),
    }

    nagaland.insert(0, record)
    nagaland.sort(
        key=lambda x: (x["date"], DRAW_ORDER.get(x["draw"], 0)),
        reverse=True
    )
    results["nagaland"] = nagaland[:MAX_HISTORY]

    log.info(f"✓ NEW: {date} {draw} | {record['draw_name']}")
    log.info(f"  Image : {image_store[:90]}")
    log.info(f"  PDF   : {pdf_url or 'N/A'}")
    log.info(f"  Attempts: {attempt}")
    return True

# ── Main ───────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="Lottery Sambad scraper v4")
    p.add_argument("--draw",     default=None,  help="1PM / 6PM / 8PM / all")
    p.add_argument("--date",     default=None,  help="YYYY-MM-DD (default: today IST)")
    p.add_argument("--no-retry", action="store_true", help="Single attempt, no retry loop")
    args = p.parse_args()

    date = args.date or ist_date()

    # 'all' mode — no retry (used for backfill)
    if args.draw == "all":
        draws  = ["1PM", "6PM", "8PM"]
        retry  = False
    elif args.draw in ("1PM", "6PM", "8PM"):
        draws  = [args.draw]
        retry  = not args.no_retry
    else:
        draws  = [auto_draw()]
        retry  = not args.no_retry

    log.info("=" * 62)
    log.info(f"bot.py v4 | IST: {ist_ts()} | Date: {date} | Draws: {draws} | Retry: {retry}")
    log.info("=" * 62)

    results     = load_results()
    any_changed = False

    for draw in draws:
        try:
            if run_draw(draw, date, results, retry=retry):
                any_changed = True
        except KeyboardInterrupt:
            log.warning("Interrupted — saving current state")
            break
        except Exception as e:
            log.error(f"Unexpected error for {draw}: {e}")
        if len(draws) > 1:
            time.sleep(3)

    results["last_updated"]  = ist_ts()
    results["total_records"] = len(results.get("nagaland", []))
    save_results(results)

    log.info("=" * 62)
    log.info("FINAL SUMMARY:")
    for r in results.get("nagaland", [])[:9]:
        seeded = " [seed]" if r.get("seeded") else ""
        log.info(
            f"  {'✅' if r.get('image') else '❌'}"
            f"{'📄' if r.get('pdf') else '  '} "
            f"{r['date']} {r['draw']:3} | {r['draw_name']}{seeded}"
        )
    log.info(f"  Changed: {any_changed} | Total: {results['total_records']}")
    log.info("=" * 62)
    sys.exit(0 if any_changed or not retry else 0)

if __name__ == "__main__":
    main()
