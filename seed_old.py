#!/usr/bin/env python3
"""seed_old.py — 3-month historical data seeder from oldresult.html"""
import re, json, time, logging, datetime, requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("seed")

URL          = "https://lotterysambadresult.in/oldresult.html"
RESULTS_FILE = Path("results.json")
MAX_HISTORY  = 270   # 90 days × 3 draws

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.google.com/",
}
DRAW_ORDER = {"1PM":1,"6PM":2,"8PM":3}
DRAW_NAMES = {
    "1PM":{0:"Dear Dwarka Morning",1:"Dear Godavari Morning",2:"Dear Indus Morning",
           3:"Dear Mahanadi Morning",4:"Dear Meghna Morning",5:"Dear Narmada Morning",6:"Dear Yamuna Morning"},
    "6PM":{0:"Dear Blitzen Evening",1:"Dear Comet Evening",2:"Dear Cupid Evening",
           3:"Dear Dancer Evening",4:"Dear Dasher Evening",5:"Dear Donner Evening",6:"Dear Vixen Evening"},
    "8PM":{0:"Dear Flamingo Evening",1:"Dear Parrot Evening",2:"Dear Eagle Evening",
           3:"Dear Falcon Evening",4:"Dear Vulture Evening",5:"Dear Ostrich Evening",6:"Dear Hawk Evening"},
}

def get_name(draw, date_str):
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return DRAW_NAMES.get(draw,{}).get(dt.weekday(), f"Dear {draw}")
    except: return f"Dear {draw}"

def parse_date(txt):
    for fmt in ("%d %B %Y","%B %d %Y","%d-%B-%Y","%d/%m/%Y","%d %b %Y"):
        try: return datetime.datetime.strptime(txt.strip(), fmt).strftime("%Y-%m-%d")
        except: pass
    m = re.search(r'(\d{1,2})\s+(January|February|March|April|May|June|July|'
                  r'August|September|October|November|December)\s+(\d{4})', txt, re.I)
    if m:
        try: return datetime.datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}","%d %B %Y").strftime("%Y-%m-%d")
        except: pass
    return None

def within_90d(d):
    try:
        dt  = datetime.datetime.strptime(d, "%Y-%m-%d")
        ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5,minutes=30)
        return (ist - dt).days <= 90
    except: return False

def main():
    log.info("="*60)
    log.info(f"SEED: fetching 3-month history from {URL}")
    for attempt in range(1,4):
        try:
            r = requests.get(URL, headers=HEADERS, timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.text,"html.parser")
            log.info(f"Fetched {len(r.text):,} chars"); break
        except Exception as e:
            log.warning(f"Attempt {attempt}: {e}")
            if attempt==3: return
            time.sleep(4*attempt)

    now_ts  = (datetime.datetime.utcnow()+datetime.timedelta(hours=5,minutes=30)).strftime("%Y-%m-%dT%H:%M:%S+05:30")
    records = []
    for table in soup.find_all("table"):
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) < 3: continue
            for i, draw in enumerate(["1PM","6PM","8PM"]):
                if i >= len(cols): continue
                date = parse_date(cols[i].get_text(" ", strip=True))
                if not date or not within_90d(date): continue
                a   = cols[i].find("a", href=True)
                pdf = ""
                if a:
                    h = a["href"].strip()
                    pdf = urljoin(URL,h) if h and not h.startswith("http") else h
                records.append({"date":date,"draw":draw,"draw_name":get_name(draw,date),
                    "image":"","pdf":pdf,"source":"historical","verified":True,
                    "seeded":True,"fetched_at":now_ts})
                log.info(f"  {date} {draw} | pdf={'✅' if pdf else '❌'}")

    if not records: log.error("No records found"); return
    records.sort(key=lambda x:(x["date"],DRAW_ORDER.get(x["draw"],0)),reverse=True)

    if RESULTS_FILE.exists():
        try: ex = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
        except: ex = {"nagaland":[],"kerala":[],"last_updated":"","total_records":0}
    else:
        ex = {"nagaland":[],"kerala":[],"last_updated":"","total_records":0}

    nag  = ex.get("nagaland",[])
    keys = {(r["date"],r["draw"]) for r in nag}
    added = 0
    for rec in records:
        k = (rec["date"],rec["draw"])
        if k not in keys: nag.append(rec); keys.add(k); added+=1

    nag.sort(key=lambda x:(x["date"],DRAW_ORDER.get(x["draw"],0)),reverse=True)
    nag = nag[:MAX_HISTORY]
    ex["nagaland"]=nag; ex["last_updated"]=now_ts; ex["total_records"]=len(nag)

    tmp = RESULTS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(ex,indent=2,ensure_ascii=False),encoding="utf-8")
    tmp.replace(RESULTS_FILE)
    log.info(f"SEED DONE — {added} added | Total: {len(nag)}")
    for r in nag[:10]:
        log.info(f"  {r['date']} {r['draw']:3} | {r['draw_name']:28} | pdf={'✅' if r.get('pdf') else '❌'}")

if __name__ == "__main__":
    main()
