#!/usr/bin/env python3
"""
seed_old.py — Last 30 Days Historical Data Seeder
===================================================
Source: https://lotterysambadresult.in/oldresult.html

Scrapes table with 3 columns (1PM | 6PM | 8PM):
- date text + PDF link per cell
- Stores last 30 days (90 records = 30 days × 3 draws)
- image field is empty (bot.py fills it daily via scraping)
- PDF links stored for archive.html display

Run via:
  GitHub Actions → workflow_dispatch → seed: yes
  OR locally: python seed_old.py
"""
import re, json, time, logging, datetime, requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("seed")

URL          = "https://lotterysambadresult.in/oldresult.html"
RESULTS_FILE = Path("results.json")
MAX_RECORDS  = 90    # 30 days × 3 draws
WITHIN_DAYS  = 30    # only last 30 days

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer":         "https://www.google.com/",
    "Cache-Control":   "no-cache",
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

def get_ist():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

def get_draw_name(draw, date_str):
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return DRAW_NAMES.get(draw, {}).get(dt.weekday(), f"Dear {draw}")
    except:
        return f"Dear {draw}"

def parse_date(txt):
    """Parse date from cell text — handles '29 May 2026', 'May 29 2026' etc."""
    txt = txt.strip()
    # Try direct formats
    for fmt in ("%d %B %Y", "%B %d %Y", "%d-%B-%Y", "%d/%m/%Y",
                "%d %b %Y", "%b %d %Y"):
        try:
            return datetime.datetime.strptime(txt, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    # Regex: "29 May 2026" or "May 29 2026"
    m = re.search(
        r'(\d{1,2})\s+(January|February|March|April|May|June|July|'
        r'August|September|October|November|December)\s+(\d{4})',
        txt, re.IGNORECASE
    )
    if m:
        try:
            return datetime.datetime.strptime(
                f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %B %Y"
            ).strftime("%Y-%m-%d")
        except:
            pass
    return None

def within_days(date_str, days=30):
    """Check if date is within last N days."""
    try:
        dt  = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        ist = get_ist()
        return (ist - dt).days <= days
    except:
        return False

def fetch_page():
    """Fetch oldresult.html with retries."""
    for attempt in range(1, 4):
        try:
            log.info(f"Fetching {URL} (attempt {attempt})")
            r = requests.get(URL, headers=HEADERS, timeout=30)
            r.raise_for_status()
            log.info(f"OK — {len(r.text):,} chars")
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            log.warning(f"Attempt {attempt} failed: {e}")
            if attempt < 3:
                time.sleep(4 * attempt)
    return None

def scrape_records(soup):
    """
    Parse table from oldresult.html.
    Each row has 3 columns: 1PM | 6PM | 8PM
    Each cell: date text + optional PDF link
    """
    tables  = soup.find_all("table")
    log.info(f"Found {len(tables)} table(s)")
    records = []
    now_ts  = get_ist().strftime("%Y-%m-%dT%H:%M:%S+05:30")

    for tidx, table in enumerate(tables):
        rows = table.find_all("tr")
        log.info(f"Table {tidx}: {len(rows)} rows")

        for row in rows[1:]:   # skip header row
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            for i, draw in enumerate(["1PM", "6PM", "8PM"]):
                if i >= len(cols):
                    continue

                col  = cols[i]
                txt  = col.get_text(" ", strip=True)
                date = parse_date(txt)

                if not date:
                    continue

                # Only keep last 30 days
                if not within_days(date, WITHIN_DAYS):
                    continue

                # Extract PDF link
                a   = col.find("a", href=True)
                pdf = ""
                if a:
                    href = a["href"].strip()
                    if href:
                        pdf = urljoin(URL, href) if not href.startswith("http") else href

                records.append({
                    "date":       date,
                    "draw":       draw,
                    "draw_name":  get_draw_name(draw, date),
                    "image":      "",   # bot.py fills this during daily scrape
                    "pdf":        pdf,
                    "source":     "historical",
                    "verified":   True,
                    "seeded":     True,
                    "fetched_at": now_ts,
                })
                log.info(f"  + {date} {draw} | pdf={'✅' if pdf else '❌'}")

    return records

def load_results():
    if RESULTS_FILE.exists():
        try:
            d = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
            log.info(f"Loaded existing: {len(d.get('nagaland', []))} records")
            return d
        except Exception as e:
            log.error(f"Load error: {e}")
    return {"nagaland": [], "kerala": [], "last_updated": "", "total_records": 0}

def merge_save(existing, new_records):
    """
    Merge seeded records into existing.
    - If record exists with image (from bot.py) → keep image, update PDF if missing
    - If record doesn't exist → add it
    """
    nag  = existing.get("nagaland", [])
    # Build index of existing records
    idx  = {(r["date"], r["draw"]): i for i, r in enumerate(nag)}
    added   = 0
    updated = 0

    for rec in new_records:
        key = (rec["date"], rec["draw"])
        if key in idx:
            # Already exists — update PDF if current record has none
            existing_rec = nag[idx[key]]
            if not existing_rec.get("pdf") and rec.get("pdf"):
                existing_rec["pdf"] = rec["pdf"]
                updated += 1
        else:
            # New record — add it
            nag.append(rec)
            idx[key] = len(nag) - 1
            added += 1

    # Sort: newest date first, within same date: 8PM > 6PM > 1PM
    nag.sort(
        key=lambda x: (x["date"], DRAW_ORDER.get(x["draw"], 0)),
        reverse=True
    )
    nag = nag[:MAX_RECORDS]

    now_ts = get_ist().strftime("%Y-%m-%dT%H:%M:%S+05:30")
    existing["nagaland"]      = nag
    existing["last_updated"]  = now_ts
    existing["total_records"] = len(nag)

    # Atomic save
    tmp = RESULTS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(RESULTS_FILE)

    log.info(f"✅ Saved — {added} new, {updated} pdf-updated | Total: {len(nag)}")
    return added, updated, nag

def main():
    log.info("=" * 62)
    log.info(f"SEED: Last {WITHIN_DAYS} days from oldresult.html")
    log.info(f"URL : {URL}")
    log.info("=" * 62)

    soup = fetch_page()
    if not soup:
        log.error("Cannot fetch page — check network"); return

    records = scrape_records(soup)

    if not records:
        log.error("No records scraped — site may have changed structure")
        log.info("Check table structure at oldresult.html manually"); return

    # Sort scraped records newest first
    records.sort(
        key=lambda x: (x["date"], DRAW_ORDER.get(x["draw"], 0)),
        reverse=True
    )

    # Draw breakdown
    from collections import Counter
    draw_counts = Counter(r["draw"] for r in records)
    log.info(f"Scraped {len(records)} records: {dict(draw_counts)}")
    log.info(f"Date range: {records[-1]['date']} → {records[0]['date']}")

    existing = load_results()
    added, updated, nag = merge_save(existing, records)

    log.info("=" * 62)
    log.info(f"SEED DONE — {added} added, {updated} PDFs updated | Total: {len(nag)}")
    log.info("Latest 15 records:")
    for r in nag[:15]:
        img_ok = '✅' if r.get('image') else '⬜'
        pdf_ok = '📄' if r.get('pdf')   else '  '
        seed   = ' [seed]' if r.get('seeded') else ''
        log.info(f"  {img_ok}{pdf_ok} {r['date']} {r['draw']:3} | {r['draw_name']}{seed}")
    log.info("=" * 62)

if __name__ == "__main__":
    main()
