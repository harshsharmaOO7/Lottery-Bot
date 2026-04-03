"""
scraper.py — Official Lottery PDF Scraper
==========================================
Fetches official lottery result PDFs and metadata
from government sources. Never extracts lottery numbers.

Supported sources:
  - Nagaland State Lottery (nagalandlotteries.com)
  - Kerala State Lottery  (statelottery.kerala.gov.in)
  - Fallback mirror sites (PDF links only)

Author : Lottery Bot
Version: 2.0.0
"""

import re
import time
import logging
import datetime
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("scraper")

# ── Constants ─────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Connection": "keep-alive",
}
TIMEOUT = 15
RETRY_COUNT = 3
RETRY_DELAY = 3   # seconds between retries

# Draw name schedules (official Nagaland 2025–26)
NAGALAND_1PM = {
    0: "Dear Dwarka Morning",
    1: "Dear Godavari Morning",
    2: "Dear Indus Morning",
    3: "Dear Mahanadi Morning",
    4: "Dear Meghna Morning",
    5: "Dear Narmada Morning",
    6: "Dear Yamuna Morning",
}
NAGALAND_6PM = {
    0: "Dear Blitzen Evening",
    1: "Dear Comet Evening",
    2: "Dear Cupid Evening",
    3: "Dear Dancer Evening",
    4: "Dear Dasher Evening",
    5: "Dear Donner Evening",
    6: "Dear Vixen Evening",
}
NAGALAND_8PM = {
    0: "Dear Finch Night",
    1: "Dear Goose Night",
    2: "Dear Pelican Night",
    3: "Dear Sandpiper Night",
    4: "Dear SeaGull Night",
    5: "Dear Stork Night",
    6: "Dear Toucan Night",
}
KERALA_DRAWS = {
    0: "Win-Win",
    1: "Sthree Sakthi",
    2: "Akshaya",
    3: "Karunya Plus",
    4: "Nirmal",
    5: "Karunya",
    6: "Pournami",
}


# ── Helpers ───────────────────────────────────────────────────────────

def get_ist_now():
    """Return current datetime in IST (UTC+5:30)."""
    utc = datetime.datetime.utcnow()
    ist_offset = datetime.timedelta(hours=5, minutes=30)
    return utc + ist_offset


def detect_draw_from_time():
    """Detect which draw slot based on current IST hour."""
    hour = get_ist_now().hour
    if hour < 14:     # before 2 PM → assume 1PM draw
        return "1PM"
    elif hour < 19:   # 2 PM – 7 PM → 6PM draw
        return "6PM"
    else:             # after 7 PM → 8PM draw
        return "8PM"


def detect_draw_from_text(text: str) -> str:
    """Parse draw time from heading/title text."""
    text = text.lower()
    if any(x in text for x in ["1 pm", "1pm", "1:00", "morning"]):
        return "1PM"
    if any(x in text for x in ["6 pm", "6pm", "6:00", "evening"]):
        return "6PM"
    if any(x in text for x in ["8 pm", "8pm", "8:00", "night"]):
        return "8PM"
    return detect_draw_from_time()


def get_draw_name(state: str, draw: str) -> str:
    """Return official draw name from schedule."""
    dow = get_ist_now().weekday()   # 0=Monday … 6=Sunday
    if state == "nagaland":
        if draw == "1PM":
            return NAGALAND_1PM.get(dow, "Dear Morning")
        if draw == "6PM":
            return NAGALAND_6PM.get(dow, "Dear Evening")
        return NAGALAND_8PM.get(dow, "Dear Night")
    if state == "kerala":
        return KERALA_DRAWS.get(dow, "Daily Draw")
    return f"{state.title()} {draw}"


def fetch_html(url: str) -> BeautifulSoup | None:
    """Fetch a URL with retries and return BeautifulSoup or None."""
    for attempt in range(1, RETRY_COUNT + 1):
        try:
            log.info(f"Fetching [{attempt}/{RETRY_COUNT}]: {url}")
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
        except requests.exceptions.HTTPError as e:
            log.warning(f"HTTP error {e} for {url}")
        except requests.exceptions.ConnectionError:
            log.warning(f"Connection error for {url}")
        except requests.exceptions.Timeout:
            log.warning(f"Timeout for {url}")
        except Exception as e:
            log.warning(f"Unexpected error: {e}")
        if attempt < RETRY_COUNT:
            time.sleep(RETRY_DELAY)
    return None


def extract_pdf_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Extract all PDF href links from a page, returning absolute URLs."""
    pdf_links = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if ".pdf" in href.lower():
            absolute = urljoin(base_url, href)
            pdf_links.append(absolute)
    return pdf_links


def find_best_pdf(links: list[str], draw_hint: str) -> str | None:
    """
    Pick the most relevant PDF link.
    Priority: today's date in URL → draw time in URL → first .pdf
    """
    today = get_ist_now().strftime("%Y-%m-%d")
    today_alt = get_ist_now().strftime("%d-%m-%Y")
    today_compact = get_ist_now().strftime("%d%m%Y")
    draw_lower = draw_hint.lower().replace("pm", "pm")

    scored = []
    for url in links:
        score = 0
        url_lower = url.lower()
        if today in url_lower or today_alt in url_lower or today_compact in url_lower:
            score += 10
        if draw_lower in url_lower:
            score += 5
        scored.append((score, url))

    scored.sort(key=lambda x: x[0], reverse=True)
    if scored:
        best_score, best_url = scored[0]
        log.info(f"Best PDF (score={best_score}): {best_url}")
        return best_url
    return None


# ── State-specific scrapers ───────────────────────────────────────────

def scrape_nagaland_official(draw: str) -> dict | None:
    """
    Scrape https://www.nagalandlotteries.com/results.php
    Official government source for Nagaland lottery PDFs.
    """
    url = "https://www.nagalandlotteries.com/results.php"
    soup = fetch_html(url)
    if not soup:
        return None

    pdf_links = extract_pdf_links(soup, url)
    log.info(f"Nagaland official: found {len(pdf_links)} PDF links")

    if not pdf_links:
        # Try looking for any download links
        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            if any(x in href.lower() for x in ["result", "download", "nagaland"]):
                pdf_links.append(urljoin(url, href))

    best = find_best_pdf(pdf_links, draw)
    if not best:
        return None

    return {
        "pdf_url": best,
        "draw": draw,
        "source": url,
        "verified": True,
    }


def scrape_nagaland_sambad(draw: str) -> dict | None:
    """
    Scrape Lottery Sambad sites for Nagaland PDF links.
    These are the most up-to-date mirror sources.
    """
    sources = [
        "https://lotterysambadresult.in/",
        "https://www.lotterysambad.com/",
    ]
    for url in sources:
        soup = fetch_html(url)
        if not soup:
            continue

        pdf_links = extract_pdf_links(soup, url)
        log.info(f"Sambad [{url}]: {len(pdf_links)} PDF links")

        if pdf_links:
            best = find_best_pdf(pdf_links, draw)
            if best:
                return {
                    "pdf_url": best,
                    "draw": draw,
                    "source": url,
                    "verified": True,
                }
        time.sleep(1)

    return None


def scrape_kerala_official(draw: str = "3PM") -> dict | None:
    """
    Scrape https://statelottery.kerala.gov.in/index.php/lottery-result-view
    Official Government of Kerala lottery result PDFs.
    """
    url = "https://statelottery.kerala.gov.in/index.php/lottery-result-view"
    soup = fetch_html(url)
    if not soup:
        # Try alternate official URL
        url = "https://www.keralalotteries.net/"
        soup = fetch_html(url)
        if not soup:
            return None

    pdf_links = extract_pdf_links(soup, url)
    log.info(f"Kerala official: {len(pdf_links)} PDF links")

    best = find_best_pdf(pdf_links, draw)
    if not best:
        # Try looking for gazette/official PDF patterns
        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            if any(x in href.lower() for x in ["gazette", "result", "prize"]):
                full = urljoin(url, href)
                if full not in pdf_links:
                    pdf_links.append(full)

        best = find_best_pdf(pdf_links, draw)
        if not best:
            return None

    return {
        "pdf_url": best,
        "draw": draw,
        "source": url,
        "verified": True,
    }


def scrape_kerala_mirror(draw: str = "3PM") -> dict | None:
    """Fallback Kerala sources."""
    sources = [
        "https://www.keralalotteryresult.net/",
        "https://lotto.in/kerala-lottery-result",
    ]
    for url in sources:
        soup = fetch_html(url)
        if not soup:
            continue
        pdf_links = extract_pdf_links(soup, url)
        if pdf_links:
            best = find_best_pdf(pdf_links, draw)
            if best:
                return {
                    "pdf_url": best,
                    "draw": draw,
                    "source": url,
                    "verified": False,
                }
        time.sleep(1)
    return None


# ── Main public API ───────────────────────────────────────────────────

def get_nagaland_result(draw: str | None = None) -> dict | None:
    """
    Try all Nagaland sources in priority order.
    Returns: {"pdf_url", "draw", "draw_name", "source", "verified"} or None
    """
    if draw is None:
        draw = detect_draw_from_time()

    log.info(f"[Nagaland] Scraping for draw: {draw}")

    result = scrape_nagaland_official(draw)
    if not result:
        log.info("[Nagaland] Official failed → trying Sambad mirrors")
        result = scrape_nagaland_sambad(draw)

    if result:
        result["draw_name"] = get_draw_name("nagaland", result["draw"])
        log.info(f"[Nagaland] ✓ Found: {result['pdf_url']}")
    else:
        log.warning("[Nagaland] ✗ All sources exhausted — no PDF found")

    return result


def get_kerala_result(draw: str = "3PM") -> dict | None:
    """
    Try all Kerala sources in priority order.
    Returns: {"pdf_url", "draw", "draw_name", "source", "verified"} or None
    """
    log.info(f"[Kerala] Scraping for draw: {draw}")

    result = scrape_kerala_official(draw)
    if not result:
        log.info("[Kerala] Official failed → trying mirrors")
        result = scrape_kerala_mirror(draw)

    if result:
        result["draw_name"] = get_draw_name("kerala", result["draw"])
        log.info(f"[Kerala] ✓ Found: {result['pdf_url']}")
    else:
        log.warning("[Kerala] ✗ All sources exhausted — no PDF found")

    return result
