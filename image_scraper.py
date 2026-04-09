"""
image_scraper.py — Lottery Result Image Scraper
================================================
EXACT SCRAPER based on real HTML analysis of competitor sites.

SOURCE 1: lotterysambadresult.in
  ├─ Draw-specific pages:
  │    1PM → /nagaland-state-lottery-sambad-today-result-1-pm.html
  │    6PM → /nagaland-state-lottery-sambad-today-7-pm-result.html
  │    8PM → /lottery-sambad-today-result-08-00-pm.html
  │
  ├─ Image location in HTML:
  │    <figure class="aligncenter size-full">
  │      <img src="...wp-content/uploads/YYYY/MM/img_HASH.webp"
  │           alt="dear-lottery-sambad-8-pm-8-April-2026-winner-list"
  │           fetchpriority="high">
  │    </figure>
  │
  └─ Date verification via alt text:
       alt contains "8-April-2026" → check if today

SOURCE 2: lotterysambad.one
  ├─ Draw-specific pages:
  │    1PM → /nagaland-state-lottery-result-1-pm/
  │    6PM → /nagaland-state-lottery-result-6-pm/
  │    8PM → /nagaland-state-lottery-result-8-pm/
  │
  └─ Image location:
       <meta property="og:image" content="...wp-content/uploads/YYYY/MM/NAME.jpeg"/>
       Also: <img class="aligncenter size-full wp-image-..." fetchpriority="high">

INSTALL: pip install requests beautifulsoup4 Pillow
"""

import re
import io
import time
import logging
import datetime
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image

log = logging.getLogger("image_scraper")

# ── Directories ───────────────────────────────────────────────────────
IMAGE_DIR = Path("images")
IMAGE_DIR.mkdir(exist_ok=True)

# ── Request config ────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}
IMG_HEADERS = {
    "User-Agent": HEADERS["User-Agent"],
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": "https://lotterysambadresult.in/",
}

TIMEOUT    = 20
MAX_IMG_MB = 15
IMG_QUALITY = 88
IMG_MAX_W   = 1200

# ── IST helpers ───────────────────────────────────────────────────────

def get_ist_now() -> datetime.datetime:
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)


def ist_date_str() -> str:
    return get_ist_now().strftime("%Y-%m-%d")


def ist_day_month() -> tuple[int, str]:
    """Returns (day_int, 'April') for alt-text matching."""
    n = get_ist_now()
    months = ["January","February","March","April","May","June",
              "July","August","September","October","November","December"]
    return n.day, months[n.month - 1]


def seo_slug(state: str, draw: str, date: str) -> str:
    """nagaland-state-lottery-sambad-result-today-8pm-2026-04-09"""
    return (
        f"{state.lower().replace('_','-')}-state-lottery-"
        f"sambad-result-today-{draw.lower()}-{date}"
    )


# ── HTML fetch ────────────────────────────────────────────────────────

def fetch_page(url: str, retries: int = 3) -> BeautifulSoup | None:
    """Fetch URL and return BeautifulSoup, with retries."""
    for attempt in range(1, retries + 1):
        try:
            log.info(f"[Fetch {attempt}/{retries}] {url}")
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
        except requests.exceptions.HTTPError as e:
            log.warning(f"HTTP {e.response.status_code} from {url}")
            if e.response.status_code in (403, 429):
                time.sleep(5 * attempt)
        except requests.exceptions.ConnectionError:
            log.warning(f"Connection error: {url}")
            time.sleep(3)
        except requests.exceptions.Timeout:
            log.warning(f"Timeout: {url}")
            time.sleep(2)
        except Exception as e:
            log.warning(f"Unexpected: {e}")
    return None


# ── Image download & save ─────────────────────────────────────────────

def download_and_save(img_url: str, dest: Path, referer: str = "") -> bool:
    """Download image URL → save as optimized JPEG at dest."""
    if dest.exists() and dest.stat().st_size > 10_000:
        log.info(f"Image cached: {dest}")
        return True

    headers = dict(IMG_HEADERS)
    if referer:
        headers["Referer"] = referer

    try:
        log.info(f"Downloading image: {img_url}")
        r = requests.get(img_url, headers=headers, timeout=TIMEOUT, stream=True)
        r.raise_for_status()

        ct = r.headers.get("Content-Type", "")
        if not any(x in ct.lower() for x in ["image", "octet-stream"]):
            log.warning(f"Bad Content-Type: {ct}")
            return False

        chunks, total = [], 0
        for chunk in r.iter_content(8192):
            if chunk:
                chunks.append(chunk)
                total += len(chunk)
                if total > MAX_IMG_MB * 1024 * 1024:
                    log.warning("Image too large — aborting")
                    return False

        raw = b"".join(chunks)
        return _save_as_jpeg(raw, dest)

    except Exception as e:
        log.error(f"Download failed [{img_url}]: {e}")
        return False


def _save_as_jpeg(raw: bytes, dest: Path) -> bool:
    """Convert raw image bytes → optimized JPEG."""
    try:
        img = Image.open(io.BytesIO(raw))

        # Normalize to RGB
        if img.mode in ("RGBA", "P"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                bg.paste(img, mask=img.split()[3])
            else:
                bg.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[3])
            img = bg
        elif img.mode == "LA":
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Resize if too wide
        if img.width > IMG_MAX_W:
            ratio = IMG_MAX_W / img.width
            img = img.resize((IMG_MAX_W, int(img.height * ratio)), Image.LANCZOS)

        img.save(str(dest), "JPEG", quality=IMG_QUALITY, optimize=True)
        log.info(f"✓ Saved: {dest} ({dest.stat().st_size // 1024} KB)")
        return True

    except Exception as e:
        log.error(f"JPEG save failed: {e}")
        return False


# ════════════════════════════════════════════════════════════════
#  SOURCE 1: lotterysambadresult.in
#  ─────────────────────────────────────────────────────────────
#  HTML pattern confirmed:
#  <figure class="aligncenter size-full">
#    <img src="...wp-content/uploads/YYYY/MM/img_HASH.webp"
#         alt="dear-lottery-sambad-8-pm-8-April-2026-winner-list"
#         fetchpriority="high">
#  </figure>
# ════════════════════════════════════════════════════════════════

SITE1_BASE = "https://lotterysambadresult.in"
SITE1_DRAW_PAGES = {
    "1PM": f"{SITE1_BASE}/nagaland-state-lottery-sambad-today-result-1-pm.html",
    "6PM": f"{SITE1_BASE}/nagaland-state-lottery-sambad-today-7-pm-result.html",
    "8PM": f"{SITE1_BASE}/lottery-sambad-today-result-08-00-pm.html",
}

def scrape_site1(draw: str) -> str | None:
    """
    Scrape lotterysambadresult.in for the result image.

    Strategy (in order):
    1. Target draw-specific page → find <figure class="aligncenter size-full"> img
    2. Cross-verify via alt text (contains today's date)
    3. Homepage fallback
    4. og:image fallback
    """
    day, month = ist_day_month()
    today_in_alt = f"{day}-{month}-{get_ist_now().year}"  # e.g. "8-April-2026"

    pages_to_try = [SITE1_DRAW_PAGES.get(draw, SITE1_BASE), SITE1_BASE]

    for page_url in pages_to_try:
        soup = fetch_page(page_url)
        if not soup:
            continue

        # ── Strategy 1: <figure class="aligncenter size-full"> img ──
        figure = soup.find("figure", class_=lambda c: c and "aligncenter" in c and "size-full" in c)
        if figure:
            img_tag = figure.find("img")
            if img_tag:
                src = img_tag.get("src", "")
                alt = img_tag.get("alt", "").lower()
                log.info(f"[site1] figure img: {src}")
                log.info(f"[site1] alt text  : {alt}")

                # Verify it's today's image via alt text
                if src and "wp-content/uploads" in src:
                    if today_in_alt.lower() in alt or _alt_matches_today(alt):
                        log.info(f"[site1] ✓ Date match in alt: {alt}")
                        return src
                    else:
                        log.warning(f"[site1] Alt date mismatch. Expected '{today_in_alt}', got '{alt}'")
                        # Still return it — might be most recent even if slightly old
                        if src:
                            return src

        # ── Strategy 2: fetchpriority="high" img in wp-content/uploads ──
        high_imgs = soup.find_all("img", attrs={"fetchpriority": "high"})
        for img in high_imgs:
            src = img.get("src", "")
            if "wp-content/uploads" in src and ".webp" in src.lower():
                alt = img.get("alt", "").lower()
                log.info(f"[site1] fetchpriority img: {src}")
                if any(kw in alt for kw in ["sambad", "lottery", "dear", "result"]):
                    return src

        # ── Strategy 3: og:image ──
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            src = og["content"]
            if "wp-content/uploads" in src:
                log.info(f"[site1] og:image: {src}")
                return src

        # ── Strategy 4: Any large wp-content img ──
        for img in soup.find_all("img", src=True):
            src = img.get("src", "")
            if "wp-content/uploads" not in src:
                continue
            # Skip thumbnails (-150x150, -300x200 etc.)
            if re.search(r"-\d{2,3}x\d{2,3}\.", src):
                continue
            # Skip logos, icons
            if any(x in src.lower() for x in ["logo", "icon", "avatar", "banner"]):
                continue
            alt = img.get("alt", "").lower()
            if any(kw in alt for kw in ["sambad", "lottery", "result", "dear", "winner"]):
                log.info(f"[site1] fallback img: {src}")
                return src

        time.sleep(1.5)

    return None


def _alt_matches_today(alt: str) -> bool:
    """Check if alt text date matches today (handles various formats)."""
    n   = get_ist_now()
    day = str(n.day)
    yr  = str(n.year)
    months = ["january","february","march","april","may","june",
              "july","august","september","october","november","december"]
    month = months[n.month - 1]
    return day in alt and month in alt and yr in alt


# ════════════════════════════════════════════════════════════════
#  SOURCE 2: lotterysambad.one
#  ─────────────────────────────────────────────────────────────
#  HTML pattern confirmed:
#  <meta property="og:image"
#        content="...wp-content/uploads/2026/04/mn84_1.jpeg"/>
#  Also: <img class="aligncenter size-full wp-image-..." fetchpriority="high">
# ════════════════════════════════════════════════════════════════

SITE2_BASE = "https://lotterysambad.one"
SITE2_DRAW_PAGES = {
    "1PM": f"{SITE2_BASE}/nagaland-state-lottery-result-1-pm/",
    "6PM": f"{SITE2_BASE}/nagaland-state-lottery-result-6-pm/",
    "8PM": f"{SITE2_BASE}/nagaland-state-lottery-result-8-pm/",
}

def scrape_site2(draw: str) -> str | None:
    """
    Scrape lotterysambad.one for the result image.

    Strategy:
    1. Draw-specific page → og:image meta (MOST RELIABLE — Yoast SEO sets this)
    2. fetchpriority="high" img with wp-image class
    3. Homepage og:image
    """
    pages_to_try = [SITE2_DRAW_PAGES.get(draw, SITE2_BASE), SITE2_BASE]

    for page_url in pages_to_try:
        soup = fetch_page(page_url)
        if not soup:
            continue

        # ── Strategy 1: og:image (Yoast SEO always sets this = post featured image) ──
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            src = og["content"]
            if "wp-content/uploads" in src:
                log.info(f"[site2] og:image: {src}")
                return src

        # ── Strategy 2: twitter:image ──
        tw = soup.find("meta", attrs={"name": "twitter:image"}) or \
             soup.find("meta", property="twitter:image")
        if tw and tw.get("content"):
            src = tw["content"]
            if "wp-content/uploads" in src:
                log.info(f"[site2] twitter:image: {src}")
                return src

        # ── Strategy 3: img with fetchpriority="high" and wp-image class ──
        for img in soup.find_all("img", attrs={"fetchpriority": "high"}):
            src   = img.get("src", "")
            cls   = " ".join(img.get("class", []))
            if "wp-content/uploads" in src and "wp-image" in cls:
                # Skip thumbnails
                if not re.search(r"-\d{2,3}x\d{2,3}\.", src):
                    log.info(f"[site2] fetchpriority wp-image: {src}")
                    return src

        # ── Strategy 4: Any large upload image ──
        for img in soup.find_all("img", src=lambda s: s and "wp-content/uploads" in s):
            src = img.get("src", "")
            if re.search(r"-\d{2,3}x\d{2,3}\.", src):
                continue
            alt = img.get("alt", "").lower()
            if any(kw in alt for kw in ["result", "lottery", "sambad", "nagaland"]):
                log.info(f"[site2] fallback: {src}")
                return src

        time.sleep(1.5)

    return None


# ════════════════════════════════════════════════════════════════
#  MAIN PUBLIC API
# ════════════════════════════════════════════════════════════════

def get_result_image(
    state:    str = "nagaland",
    draw:     str = "8PM",
    date_str: str | None = None,
) -> str:
    """
    Fetch today's lottery result image.

    Priority order:
      1. lotterysambadresult.in (updates fastest, most consistent HTML)
      2. lotterysambad.one      (og:image via Yoast — very reliable)

    Returns local path like "images/nagaland-state-...-8pm-2026-04-09.jpg"
    or "" if both sources fail.
    """
    if date_str is None:
        date_str = ist_date_str()

    slug = seo_slug(state, draw, date_str)
    dest = IMAGE_DIR / f"{slug}.jpg"

    # Already downloaded today
    if dest.exists() and dest.stat().st_size > 10_000:
        log.info(f"Using cached image: {dest}")
        return str(dest).replace("\\", "/")

    # ── Attempt 1: lotterysambadresult.in ──
    if state == "nagaland":
        log.info(f"[Source 1] lotterysambadresult.in → {draw}")
        img_url = scrape_site1(draw)
        if img_url:
            referer = SITE1_DRAW_PAGES.get(draw, SITE1_BASE)
            if download_and_save(img_url, dest, referer=referer):
                log.info(f"✅ Image from site1: {dest}")
                return str(dest).replace("\\", "/")
            else:
                log.warning("Site1 image download failed")
        else:
            log.warning("Site1: no image URL found")

        time.sleep(2)

        # ── Attempt 2: lotterysambad.one ──
        log.info(f"[Source 2] lotterysambad.one → {draw}")
        img_url = scrape_site2(draw)
        if img_url:
            referer = SITE2_DRAW_PAGES.get(draw, SITE2_BASE)
            # Update referer header for site2
            global IMG_HEADERS
            IMG_HEADERS["Referer"] = referer
            if download_and_save(img_url, dest, referer=referer):
                log.info(f"✅ Image from site2: {dest}")
                return str(dest).replace("\\", "/")
            else:
                log.warning("Site2 image download failed")
        else:
            log.warning("Site2: no image URL found")

    log.warning(f"❌ All image sources failed for {state} {draw} {date_str}")
    return ""


# ════════════════════════════════════════════════════════════════
#  STANDALONE TEST RUNNER
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    draw = sys.argv[1].upper() if len(sys.argv) > 1 else "8PM"
    if draw not in ("1PM", "6PM", "8PM"):
        print("Usage: python image_scraper.py [1PM|6PM|8PM]")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"  Lottery Image Scraper — {draw}")
    print(f"  IST Date : {ist_date_str()}")
    print(f"{'='*50}\n")

    result = get_result_image("nagaland", draw)

    print(f"\n{'='*50}")
    if result:
        print(f"  ✅ SUCCESS")
        print(f"  Saved to : {result}")
        # Show image info
        try:
            img = Image.open(result)
            print(f"  Size     : {img.width}×{img.height} px")
            import os
            print(f"  File size: {os.path.getsize(result) // 1024} KB")
        except Exception:
            pass
    else:
        print("  ❌ FAILED — No image obtained")
        print("\n  Possible reasons:")
        print("  • Both sites blocked the request (try again later)")
        print("  • Result not yet published (check after draw time)")
        print("  • Site structure changed (check HTML manually)")
    print(f"{'='*50}\n")
