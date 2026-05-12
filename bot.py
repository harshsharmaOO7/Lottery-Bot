#!/usr/bin/env python3
"""
bot.py — Lottery Sambad Daily Scraper (Fixed)
===============================================
FIX: Results now properly sorted — newest date first, 8PM > 6PM > 1PM within same date.
FIX: MAX_HISTORY = 90 (3 draws x 30 days)
FIX: draw explicitly passed from workflow — no more auto_draw() mismatch
"""
import sys, re, json, time, logging, argparse, datetime, requests, shutil
from pathlib import Path
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("bot")

RESULTS_FILE = Path("results.json")
IMAGES_DIR   = Path("images")
MAX_HISTORY  = 90   # 3 draws x 30 days

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer":         "https://www.google.com/",
    "Cache-Control":   "no-cache",
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

# ── Fetch ──────────────────────────────────────────────────────────────────
def fetch_page(url):
    for attempt in range(1, 4):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            log.info(f"Fetched {len(r.text):,} chars (attempt {attempt})")
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            log.warning(f"Attempt {attempt} failed: {e}")
            time.sleep(4 * attempt)
    return None

# ── Image extraction ───────────────────────────────────────────────────────
def is_thumbnail(url):
    return bool(re.search(r"-\d{2,3}x\d{2,3}\.", url))

def date_in_alt(alt, ist_dt):
    months = ["january","february","march","april","may","june",
              "july","august","september","october","november","december"]
    alt_l = alt.lower()
    d, mo, yr = str(ist_dt.day), months[ist_dt.month-1], str(ist_dt.year)
    return any(p in alt_l for p in [
        f"{d}-{mo}-{yr}", f"{d} {mo} {yr}",
        f"{mo}-{d}-{yr}", f"{mo} {d} {yr}",
        f"{d.zfill(2)}/{str(ist_dt.month).zfill(2)}/{yr}",
    ])

def extract_image(soup, draw, ist_dt):
    # S1: confirmed figure pattern
    fig = soup.find("figure", class_=lambda c: c and "aligncenter" in c and "size-full" in c)
    if fig:
        img = fig.find("img")
        if img:
            src = img.get("src", "").strip()
            alt = img.get("alt", "").strip()
            if src and "wp-content/uploads" in src and not is_thumbnail(src):
                is_today = date_in_alt(alt, ist_dt)
                log.info(f"[S1] src={src[:80]} | today={is_today}")
                return src, is_today

    # S2: scored scan
    candidates = []
    for img in soup.find_all("img", src=True):
        src = img.get("src", "")
        alt = img.get("alt", "").lower()
        if "wp-content/uploads" not in src or is_thumbnail(src): continue
        if any(x in src.lower() for x in ["logo","banner","favicon","icon"]): continue
        score = 0
        if any(k in alt for k in ["sambad","result","lottery","dear","nagaland"]): score += 4
        if draw.replace("PM","") in alt: score += 3
        if date_in_alt(alt, ist_dt): score += 8
        if src.endswith((".webp",".jpg",".jpeg")): score += 1
        if score > 0:
            candidates.append((score, src, date_in_alt(alt, ist_dt)))

    if candidates:
        candidates.sort(reverse=True)
        sc, src, is_today = candidates[0]
        log.info(f"[S2] Best score={sc} today={is_today}: {src[:80]}")
        return src, is_today

    return None, False

def extract_pdf(soup):
    dl = soup.find("a", class_=lambda c: c and "download_btn" in c)
    if dl:
        href = dl.get("href","")
        if href and ".pdf" in href.lower(): return href
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf") and "wp-content" in href: return href
    return None

# ── Image download ─────────────────────────────────────────────────────────
def download_image(img_url, draw, date):
    IMAGES_DIR.mkdir(exist_ok=True)
    ext  = "webp" if img_url.lower().endswith(".webp") else "jpg"
    name = f"nagaland-{draw.lower()}-{date}.{ext}"
    path = IMAGES_DIR / name
    if path.exists() and path.stat().st_size > 5000:
        log.info(f"Already exists: {name}")
        return name
    try:
        r = requests.get(img_url, headers={**HEADERS, "Referer":"https://lotterysambadresult.in/"},
                         timeout=30, stream=True)
        r.raise_for_status()
        with open(path, "wb") as f:
            shutil.copyfileobj(r.raw, f)
        log.info(f"Downloaded: {name} ({path.stat().st_size//1024}KB)")
        return name
    except Exception as e:
        log.warning(f"Download failed: {e}")
        return None

# ── JSON ───────────────────────────────────────────────────────────────────
def load_results():
    if RESULTS_FILE.exists():
        try:
            d = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
            log.info(f"Loaded {len(d.get('nagaland',[]))} nagaland records")
            return d
        except Exception as e:
            log.error(f"Load error: {e}")
    return {"nagaland":[], "kerala":[], "last_updated":"", "total_records":0}

def save_results(data):
    tmp = RESULTS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(RESULTS_FILE)
    log.info(f"✓ Saved ({RESULTS_FILE.stat().st_size:,} bytes)")

# ── Draw runner ────────────────────────────────────────────────────────────
def run_draw(draw, date, results):
    log.info(f"{'='*20} {draw} | {date} {'='*20}")
    soup = fetch_page(SOURCE_PAGES[draw])
    if not soup:
        log.error(f"Fetch failed for {draw}"); return False

    try:
        ist_dt = datetime.datetime.strptime(date, "%Y-%m-%d")
    except:
        ist_dt = get_ist()

    img_url, is_today = extract_image(soup, draw, ist_dt)
    pdf_url           = extract_pdf(soup)

    if not img_url:
        log.warning(f"No image for {draw} {date}"); return False

    # Download locally
    local = download_image(img_url, draw, date)
    image_store = f"images/{local}" if local else img_url

    nagaland = results.setdefault("nagaland", [])
    existing = next((r for r in nagaland if r.get("date")==date and r.get("draw")==draw), None)

    if existing:
        changed = False
        if existing.get("image") != image_store:
            existing["image"] = image_store; changed = True
        if pdf_url and existing.get("pdf") != pdf_url:
            existing["pdf"] = pdf_url; changed = True
        if changed:
            existing["fetched_at"] = ist_ts()
            existing.pop("seeded", None)
            log.info(f"✓ Updated {date} {draw}")
        else:
            log.info("No change")
        return changed

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
    nagaland.append(record)

    # FIXED SORT: newest date first, within same date: 8PM > 6PM > 1PM
    nagaland.sort(
        key=lambda x: (x["date"], DRAW_ORDER.get(x["draw"], 0)),
        reverse=True
    )
    results["nagaland"] = nagaland[:MAX_HISTORY]

    log.info(f"✓ New: {date} {draw} | {record['draw_name']}")
    log.info(f"  img={image_store[:80]}")
    log.info(f"  pdf={pdf_url or 'N/A'}")
    return True

# ── Main ───────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--draw", default=None, help="1PM/6PM/8PM/all")
    p.add_argument("--date", default=None, help="YYYY-MM-DD (default: today IST)")
    args = p.parse_args()

    date = args.date or ist_date()

    if args.draw == "all":
        draws = ["1PM","6PM","8PM"]
    elif args.draw in ("1PM","6PM","8PM"):
        draws = [args.draw]
    else:
        # Fallback auto-detect (only used locally, never from workflow)
        h = get_ist().hour
        draws = ["1PM" if h < 13 else "6PM" if h < 18 else "8PM"]

    log.info("="*62)
    log.info(f"Bot | IST: {ist_ts()} | Date: {date} | Draws: {draws}")
    log.info("="*62)

    results     = load_results()
    any_changed = False

    for draw in draws:
        try:
            if run_draw(draw, date, results): any_changed = True
        except Exception as e:
            log.error(f"Error {draw}: {e}")
        if len(draws) > 1: time.sleep(2)

    results["last_updated"]  = ist_ts()
    results["total_records"] = len(results.get("nagaland",[]))
    save_results(results)

    log.info("="*62)
    for r in results.get("nagaland",[])[:9]:
        log.info(f"  {'✅' if r.get('image') else '❌'} {r['date']} {r['draw']:3} | {r['draw_name']}")
    log.info(f"Changed={any_changed} Total={results['total_records']}")
    log.info("="*62)

if __name__ == "__main__":
    main()
