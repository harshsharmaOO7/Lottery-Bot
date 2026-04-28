#!/usr/bin/env python3
"""
seed_old.py — One-time historical data seeder
==============================================
Scrapes oldresult.html table → populates results.json with last 90 records.
Run ONCE via GitHub Actions (workflow_dispatch → job: seed).
After seeding, daily bot.py handles new results automatically.

Source: https://lotterysambadresult.in/oldresult.html
"""
import re, json, time, logging, datetime, requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("seed")

URL          = "https://lotterysambadresult.in/oldresult.html"
RESULTS_FILE = Path("results.json")
MAX_HISTORY  = 90

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.google.com/",
    "Cache-Control": "no-cache",
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

def get_draw_name(draw, date_str):
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return DRAW_NAMES.get(draw, {}).get(dt.weekday(), f"Dear {draw}")
    except Exception:
        return f"Dear {draw}"

def parse_date(txt):
    txt = txt.strip()
    for fmt in ("%d %B %Y", "%B %d %Y", "%d-%B-%Y", "%d/%m/%Y", "%B %d, %Y"):
        try:
            return datetime.datetime.strptime(txt, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Regex fallback
    m = re.search(
        r'(\d{1,2})\s+(January|February|March|April|May|June|July|'
        r'August|September|October|November|December)\s+(\d{4})',
        txt, re.I
    )
    if m:
        try:
            return datetime.datetime.strptime(
                f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %B %Y"
            ).strftime("%Y-%m-%d")
        except Exception:
            pass
    return None

def fetch_old():
    log.info(f"Fetching: {URL}")
    for attempt in range(1, 4):
        try:
            r = requests.get(URL, headers=HEADERS, timeout=30)
            r.raise_for_status()
            log.info(f"OK — {len(r.text):,} chars")
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            log.warning(f"Attempt {attempt} failed: {e}")
            if attempt < 3:
                time.sleep(3 * attempt)
    return None

def scrape_records(soup):
    tables = soup.find_all("table")
    log.info(f"Found {len(tables)} table(s)")
    records = []

    for tidx, table in enumerate(tables):
        rows = table.find_all("tr")
        log.info(f"Table {tidx}: {len(rows)} rows")

        for row in rows[1:]:   # skip header
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

                # PDF link in this cell
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
                    "image":      "",    # historical — no image URL available
                    "pdf":        pdf,
                    "source":     URL,
                    "verified":   True,
                    "seeded":     True,  # marks as historical seed
                    "fetched_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                })
                log.info(f"  + {date} {draw} | pdf={'✅' if pdf else '❌'}")

    return records

def load_existing():
    if RESULTS_FILE.exists():
        try:
            data = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
            log.info(f"Existing: {len(data.get('nagaland', []))} records")
            return data
        except Exception as e:
            log.error(f"Load error: {e}")
    return {"nagaland": [], "kerala": [], "last_updated": "", "total_records": 0}

def merge_save(existing, new_records):
    nagaland = existing.get("nagaland", [])
    existing_keys = {(r["date"], r["draw"]) for r in nagaland}

    added = 0
    for rec in new_records:
        key = (rec["date"], rec["draw"])
        if key not in existing_keys:
            nagaland.append(rec)
            existing_keys.add(key)
            added += 1

    # Sort newest first, 8PM > 6PM > 1PM
    nagaland.sort(
        key=lambda x: (x["date"], DRAW_ORDER.get(x["draw"], 0)),
        reverse=True
    )
    nagaland = nagaland[:MAX_HISTORY]

    existing["nagaland"]      = nagaland
    existing["last_updated"]  = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00")
    existing["total_records"] = len(nagaland)

    tmp = RESULTS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(RESULTS_FILE)

    log.info(f"✅ Saved: {len(nagaland)} total | {added} new seeded")
    return added, nagaland

def main():
    log.info("=" * 60)
    log.info("SEED OLD RESULTS — One-time historical seeder")
    log.info("=" * 60)

    soup = fetch_old()
    if not soup:
        log.error("Could not fetch oldresult.html — aborting")
        return

    records = scrape_records(soup)
    log.info(f"\nScraped: {len(records)} raw records")

    if not records:
        log.error("No records found — check table structure on oldresult.html")
        return

    # Sort and keep latest 90
    records.sort(
        key=lambda x: (x["date"], DRAW_ORDER.get(x["draw"], 0)),
        reverse=True
    )
    records = records[:MAX_HISTORY]
    log.info(f"Keeping latest: {len(records)}")

    existing = load_existing()
    added, nagaland = merge_save(existing, records)

    log.info("=" * 60)
    log.info(f"SEED COMPLETE — {added} records added")
    log.info("Latest 10:")
    for r in nagaland[:10]:
        log.info(f"  {r['date']} {r['draw']:3} | {r['draw_name']:30} | pdf={'✅' if r.get('pdf') else '❌'}")
    log.info("=" * 60)

if __name__ == "__main__":
    main()
