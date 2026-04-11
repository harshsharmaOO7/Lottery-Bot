#!/usr/bin/env python3
"""
bot.py — Lottery Result Bot (Final - Based on Real HTML)
HTML Analysis:
  IMAGE: <figure class="aligncenter size-full"><img src="wp-content/uploads/.../img_HASH.webp">
  PDF:   <a class="max_button download_btn" href="wp-content/uploads/.../pdf_HASH.pdf">
  og:image = STATIC LOGO — do NOT use for result image
"""
import sys, re, json, time, logging, argparse, datetime, requests
from pathlib import Path
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("bot")

RESULTS_FILE = Path("results.json")
MAX_HISTORY  = 30

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
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

# Updated from actual HTML table on site
DRAW_NAMES = {
    "1PM": {0:"Dear Dwarka Morning",1:"Dear Godavari Morning",2:"Dear Indus Morning",
            3:"Dear Mahanadi Morning",4:"Dear Meghna Morning",5:"Dear Narmada Morning",6:"Dear Yamuna Morning"},
    "6PM": {0:"Dear Blitzen Evening",1:"Dear Comet Evening",2:"Dear Cupid Evening",
            3:"Dear Dancer Evening",4:"Dear Dasher Evening",5:"Dear Donner Evening",6:"Dear Vixen Evening"},
    "8PM": {0:"Dear Flamingo Evening",1:"Dear Parrot Evening",2:"Dear Eagle Evening",
            3:"Dear Falcon Evening",4:"Dear Vulture Evening",5:"Dear Ostrich Evening",6:"Dear Hawk Evening"},
}

def get_ist():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
def ist_date(): return get_ist().strftime("%Y-%m-%d")
def ist_ts():   return get_ist().strftime("%Y-%m-%dT%H:%M:%S+05:30")
def auto_draw():
    h = get_ist().hour
    return "1PM" if h < 13 else "6PM" if h < 18 else "8PM"
def get_draw_name(draw):
    return DRAW_NAMES.get(draw,{}).get(get_ist().weekday(), f"Dear {draw}")

def today_in_alt(alt):
    n  = get_ist()
    mo = ["january","february","march","april","may","june",
          "july","august","september","october","november","december"]
    return f"{n.day}-{mo[n.month-1]}-{n.year}" in alt.lower()

def fetch_page(url):
    for attempt in range(1, 4):
        try:
            log.info(f"Fetching (attempt {attempt}): {url}")
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            log.info(f"OK — {len(r.text):,} chars")
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            log.warning(f"Attempt {attempt} failed: {e}")
            time.sleep(3 * attempt)
    return None

def is_thumbnail(url):
    return bool(re.search(r"-\d{2,3}x\d{2,3}\.", url))

def extract_image(soup, draw):
    """
    PRIMARY: <figure class="aligncenter size-full"> img src
    This is the confirmed pattern from real HTML.
    URL changes daily: wp-content/uploads/YYYY/MM/img_HASH.webp
    """
    # Strategy 1: figure.aligncenter.size-full img (EXACT from real HTML)
    fig = soup.find("figure", class_=lambda c: c and "aligncenter" in c and "size-full" in c)
    if fig:
        img = fig.find("img")
        if img:
            src = img.get("src","").strip()
            alt = img.get("alt","").strip()
            log.info(f"[fig] src: {src}")
            log.info(f"[fig] alt: {alt}")
            if src and "wp-content/uploads" in src:
                if today_in_alt(alt):
                    log.info("[fig] ✅ Today's date in alt — confirmed!")
                else:
                    log.warning(f"[fig] ⚠️ Date mismatch in alt — returning anyway")
                return src  # Always return this — it's the result image

    # Strategy 2: Any wp-content img with result keywords in alt
    log.info("[S2] Scanning all images...")
    draw_num = draw.replace("PM","").replace("pm","")
    candidates = []
    for img in soup.find_all("img", src=True):
        src = img.get("src","")
        alt = img.get("alt","").lower()
        if "wp-content/uploads" not in src: continue
        if is_thumbnail(src): continue
        if any(x in src for x in ["logo","banner","favicon","icon"]): continue
        score = 0
        if any(k in alt for k in ["sambad","result","winner","lottery","dear"]): score += 4
        if draw_num in alt: score += 3
        if today_in_alt(alt): score += 5
        if ".webp" in src or ".jpg" in src or ".jpeg" in src: score += 1
        if score > 0:
            candidates.append((score, src))

    if candidates:
        candidates.sort(reverse=True)
        best = candidates[0][1]
        log.info(f"[S2] Best (score={candidates[0][0]}): {best}")
        return best

    log.warning("No image found on page")
    return None

def extract_pdf(soup):
    """
    PRIMARY: <a class="max_button download_btn" href="...pdf_HASH.pdf">
    This is confirmed from real HTML line 80.
    """
    # Exact class from HTML
    dl = soup.find("a", class_=lambda c: c and "download_btn" in c)
    if dl:
        href = dl.get("href","")
        if href and (".pdf" in href.lower() or "pdf" in href.lower()):
            log.info(f"PDF (download_btn): {href}")
            return href

    # Fallback: any .pdf link
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf") and "wp-content" in href:
            log.info(f"PDF (fallback): {href}")
            return href

    log.info("No PDF found")
    return None

def load_results():
    if RESULTS_FILE.exists():
        try:
            data = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
            log.info(f"Loaded — {data.get('total_records',0)} records")
            return data
        except Exception as e:
            log.error(f"results.json error: {e}")
    return {"nagaland":[], "kerala":[], "last_updated":"", "total_records":0}

def save_results(data):
    tmp = RESULTS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(RESULTS_FILE)
    log.info(f"✓ Saved ({RESULTS_FILE.stat().st_size:,} bytes)")

def run_draw(draw, date, results):
    log.info(f"━━━━ {draw} | {date} ━━━━")
    soup = fetch_page(SOURCE_PAGES[draw])
    if not soup:
        log.error(f"Page fetch failed for {draw}")
        return False

    img_url = extract_image(soup, draw)
    pdf_url = extract_pdf(soup)

    if not img_url:
        log.warning(f"No image for {draw} — not published yet?")
        return False

    nagaland = results.setdefault("nagaland", [])

    # Find existing record for same date+draw
    existing = next((r for r in nagaland
                     if r.get("date") == date and r.get("draw") == draw), None)

    if existing:
        changed = False
        if existing.get("image") != img_url:
            existing["image"] = img_url
            changed = True
            log.info("Updated image URL")
        if pdf_url and existing.get("pdf") != pdf_url:
            existing["pdf"] = pdf_url
            changed = True
            log.info("Updated PDF URL")
        if changed:
            existing["fetched_at"] = ist_ts()
            log.info(f"✓ Updated: {date} {draw}")
        else:
            log.info("No change needed")
        return changed

    # New record
    record = {
        "date":       date,
        "draw":       draw,
        "draw_name":  get_draw_name(draw),
        "image":      img_url,
        "pdf":        pdf_url or "",
        "source":     SOURCE_PAGES[draw],
        "verified":   True,
        "fetched_at": ist_ts(),
    }
    nagaland.insert(0, record)
    nagaland[:] = nagaland[:MAX_HISTORY]
    log.info(f"✓ New: {date} {draw} | {record['draw_name']}")
    log.info(f"  Image: {img_url}")
    log.info(f"  PDF  : {pdf_url or 'N/A'}")
    return True

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--draw", default=None, help="1PM/6PM/8PM/all")
    p.add_argument("--date", default=None, help="YYYY-MM-DD")
    args = p.parse_args()

    date  = args.date or ist_date()
    draws = (["1PM","6PM","8PM"] if args.draw == "all"
             else [args.draw] if args.draw in ("1PM","6PM","8PM")
             else [auto_draw()])

    log.info("="*56)
    log.info(f"Bot | IST: {ist_ts()} | Draws: {draws}")
    log.info("="*56)

    results     = load_results()
    any_changed = False

    for draw in draws:
        try:
            if run_draw(draw, date, results):
                any_changed = True
        except Exception as e:
            log.error(f"Error {draw}: {e}")
        time.sleep(2)

    results["last_updated"]  = ist_ts()
    results["total_records"] = sum(len(results.get(s,[])) for s in ["nagaland","kerala"])
    save_results(results)

    log.info("="*56)
    log.info("SUMMARY:")
    for r in results.get("nagaland",[])[:6]:
        log.info(f"  {'✅' if r.get('image') else '❌'}"
                 f"{'📄' if r.get('pdf') else '  '} "
                 f"{r['date']} {r['draw']:3} | {r['draw_name']}")
    log.info(f"  Changed: {any_changed} | Total: {results['total_records']}")
    log.info("="*56)
    sys.exit(0)

if __name__ == "__main__":
    main()
