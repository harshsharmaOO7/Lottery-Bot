#!/usr/bin/env python3
"""
seed_old.py v2 — 3 Months Historical Data Seeder
==================================================
Scrapes lotterysambadresult.in/oldresult.html
→ stores last 3 months (270 records = 90 days x 3 draws) in results.json

Run ONCE on first deploy:
  GitHub Actions → workflow_dispatch → job: seed

After seeding, daily bot.py handles all new results automatically.
"""
import re, json, time, logging, datetime, requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("seed")

OLD_URL      = "https://lotterysambadresult.in/oldresult.html"
RESULTS_FILE = Path("results.json")
MAX_HISTORY  = 270   # 90 days x 3 draws

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
    except:
        return f"Dear {draw}"

def parse_date(txt):
    txt = txt.strip()
    for fmt in ("%d %B %Y", "%B %d %Y", "%d-%B-%Y", "%d/%m/%Y", "%B %d, %Y", "%d %b %Y"):
        try:
            return datetime.datetime.strptime(txt, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
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
        except:
            pass
    return None

def within_3_months(date_str):
    try:
        dt  = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
        return (ist.replace(tzinfo=None) - dt).days <= 90
    except:
        return False

def fetch_soup(url):
    for i in range(1, 4):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            log.info(f"Fetched {len(r.text):,} chars")
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            log.warning(f"Attempt {i}: {e}")
            if i < 3: time.sleep(4 * i)
    return None

def scrape(soup):
    tables  = soup.find_all("table")
    log.info(f"{len(tables)} table(s) found")
    records = []
    now_ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

    for tidx, table in enumerate(tables):
        rows = table.find_all("tr")
        log.info(f"Table {tidx}: {len(rows)} rows")
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) < 3: continue
            for i, draw in enumerate(["1PM", "6PM", "8PM"]):
                if i >= len(cols): continue
                col  = cols[i]
                txt  = col.get_text(" ", strip=True)
                date = parse_date(txt)
                if not date: continue
                if not within_3_months(date): continue

                a   = col.find("a", href=True)
                pdf = ""
                if a:
                    href = a["href"].strip()
                    pdf  = urljoin(OLD_URL, href) if href and not href.startswith("http") else href

                records.append({
                    "date":       date,
                    "draw":       draw,
                    "draw_name":  get_draw_name(draw, date),
                    "image":      "",    # oldresult.html has no result images
                    "pdf":        pdf,
                    "source":     "historical",
                    "verified":   True,
                    "seeded":     True,
                    "fetched_at": now_ist.strftime("%Y-%m-%dT%H:%M:%S+05:30"),
                })
                log.info(f"  + {date} {draw} | pdf={'✅' if pdf else '❌'}")
    return records

def load():
    if RESULTS_FILE.exists():
        try:
            d = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
            log.info(f"Existing: {len(d.get('nagaland', []))} records")
            return d
        except: pass
    return {"nagaland": [], "kerala": [], "last_updated": "", "total_records": 0}

def save(existing, new_records):
    nag   = existing.get("nagaland", [])
    keys  = {(r["date"], r["draw"]) for r in nag}
    added = 0
    for rec in new_records:
        k = (rec["date"], rec["draw"])
        if k not in keys:
            nag.append(rec); keys.add(k); added += 1

    nag.sort(key=lambda x: (x["date"], DRAW_ORDER.get(x["draw"], 0)), reverse=True)
    nag = nag[:MAX_HISTORY]

    existing["nagaland"]      = nag
    existing["last_updated"]  = (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).strftime("%Y-%m-%dT%H:%M:%S+05:30")
    existing["total_records"] = len(nag)

    tmp = RESULTS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(RESULTS_FILE)
    log.info(f"✅ Saved {len(nag)} total ({added} new)")
    return added, nag

def main():
    log.info("=" * 60)
    log.info("SEED v2 — Last 3 Months Historical Data")
    log.info(f"Source : {OLD_URL}")
    log.info("=" * 60)

    soup = fetch_soup(OLD_URL)
    if not soup:
        log.error("Cannot fetch oldresult.html"); return

    records = scrape(soup)
    if not records:
        log.error("No records scraped — site structure may have changed"); return

    records.sort(key=lambda x: (x["date"], DRAW_ORDER.get(x["draw"], 0)), reverse=True)
    log.info(f"Scraped {len(records)} records | Range: {records[-1]['date']} → {records[0]['date']}")

    existing      = load()
    added, result = save(existing, records)

    log.info("=" * 60)
    log.info(f"SEED COMPLETE — {added} records added | Total: {len(result)}")
    log.info("Latest 15:")
    for r in result[:15]:
        log.info(f"  {r['date']} {r['draw']:3} | {r['draw_name']:28} | pdf={'✅' if r.get('pdf') else '❌'}")
    log.info("=" * 60)

if __name__ == "__main__":
    main()
