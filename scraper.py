"""
scraper.py — Lottery PDF Metadata Scraper v3
=============================================
Fetches PDF URLs and draw metadata from official sources.
Does NOT extract lottery numbers.

Author : Lottery Bot v3
"""

import re
import time
import logging
import datetime
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

log = logging.getLogger("scraper")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}
TIMEOUT     = 15
RETRY       = 3
RETRY_DELAY = 3

# Official draw name schedules
NAGALAND_1PM = {0:"Dear Dwarka Morning",1:"Dear Godavari Morning",2:"Dear Indus Morning",
                3:"Dear Mahanadi Morning",4:"Dear Meghna Morning",5:"Dear Narmada Morning",6:"Dear Yamuna Morning"}
NAGALAND_6PM = {0:"Dear Blitzen Evening",1:"Dear Comet Evening",2:"Dear Cupid Evening",
                3:"Dear Dancer Evening",4:"Dear Dasher Evening",5:"Dear Donner Evening",6:"Dear Vixen Evening"}
NAGALAND_8PM = {0:"Dear Finch Night",1:"Dear Goose Night",2:"Dear Pelican Night",
                3:"Dear Sandpiper Night",4:"Dear SeaGull Night",5:"Dear Stork Night",6:"Dear Toucan Night"}
KERALA_DRAWS = {0:"Win-Win",1:"Sthree Sakthi",2:"Akshaya",3:"Karunya Plus",
                4:"Nirmal",5:"Karunya",6:"Pournami"}


def get_ist_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)


def detect_draw_from_time():
    h = get_ist_now().hour
    if h < 14:      return "1PM"
    elif h < 19:    return "6PM"
    else:           return "8PM"


def detect_draw_from_text(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["1 pm", "1pm", "1:00", "morning"]):   return "1PM"
    if any(x in t for x in ["6 pm", "6pm", "6:00", "evening"]):   return "6PM"
    if any(x in t for x in ["8 pm", "8pm", "8:00", "night"]):     return "8PM"
    return detect_draw_from_time()


def get_draw_name(state: str, draw: str) -> str:
    dow = get_ist_now().weekday()
    if state == "nagaland":
        return {"1PM": NAGALAND_1PM, "6PM": NAGALAND_6PM, "8PM": NAGALAND_8PM}.get(draw, NAGALAND_8PM).get(dow, "Dear Lottery")
    if state == "kerala":
        return KERALA_DRAWS.get(dow, "Kerala Daily")
    return f"{state.title()} {draw}"


def fetch_html(url: str) -> BeautifulSoup | None:
    for attempt in range(1, RETRY + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            log.warning(f"[{attempt}/{RETRY}] {url}: {e}")
            if attempt < RETRY: time.sleep(RETRY_DELAY)
    return None


def extract_pdf_links(soup: BeautifulSoup, base: str) -> list[str]:
    links = []
    for a in soup.find_all("a", href=True):
        h = a["href"].strip()
        if ".pdf" in h.lower():
            links.append(urljoin(base, h))
    return links


def best_pdf(links: list[str], draw: str) -> str | None:
    if not links: return None
    today = get_ist_now().strftime("%Y-%m-%d")
    today_alt = get_ist_now().strftime("%d-%m-%Y")
    scored = []
    for u in links:
        s = 0
        ul = u.lower()
        if today in ul or today_alt in ul: s += 10
        if draw.lower() in ul:             s += 5
        if "pdf" in ul:                    s += 1
        scored.append((s, u))
    scored.sort(reverse=True)
    best = scored[0][1]
    log.info(f"Best PDF (score={scored[0][0]}): {best}")
    return best


def get_nagaland_result(draw: str | None = None) -> dict | None:
    if draw is None: draw = detect_draw_from_time()
    log.info(f"[Nagaland] Scraping draw: {draw}")

    # 1. Official government site
    soup = fetch_html("https://www.nagalandlotteries.com/results.php")
    result = None
    if soup:
        pdfs = extract_pdf_links(soup, "https://www.nagalandlotteries.com/")
        log.info(f"[Nagaland official] {len(pdfs)} PDF links")
        pdf = best_pdf(pdfs, draw)
        if pdf:
            result = {"pdf_url": pdf, "draw": draw, "source": "https://www.nagalandlotteries.com/results.php", "verified": True}

    # 2. Mirror fallback
    if not result:
        for url in ["https://lotterysambadresult.in/", "https://www.lotterysambad.com/"]:
            soup = fetch_html(url)
            if not soup: continue
            pdfs = extract_pdf_links(soup, url)
            pdf  = best_pdf(pdfs, draw)
            if pdf:
                result = {"pdf_url": pdf, "draw": draw, "source": url, "verified": False}
                break
            time.sleep(1)

    if result:
        result["draw_name"] = get_draw_name("nagaland", result["draw"])
        log.info(f"[Nagaland] ✓ {result['pdf_url']}")
    else:
        log.warning("[Nagaland] ✗ All sources failed")
    return result


def get_kerala_result(draw: str = "3PM") -> dict | None:
    log.info(f"[Kerala] Scraping draw: {draw}")
    sources = [
        "https://statelottery.kerala.gov.in/index.php/lottery-result-view",
        "https://www.keralalotteries.net/",
        "https://www.keralalotteryresult.net/",
    ]
    for url in sources:
        soup = fetch_html(url)
        if not soup: continue
        pdfs = extract_pdf_links(soup, url)
        pdf  = best_pdf(pdfs, draw)
        if pdf:
            result = {"pdf_url": pdf, "draw": draw, "source": url,
                      "verified": "kerala.gov.in" in url, "draw_name": get_draw_name("kerala", draw)}
            log.info(f"[Kerala] ✓ {pdf}")
            return result
        time.sleep(1)
    log.warning("[Kerala] ✗ All sources failed")
    return None
