"""
image_scraper.py — Lottery Result Image Scraper
=================================================
Scrapes result IMAGES (not numbers) from lottery result sites.
Primary source: lotterysambadresult.in (WordPress site)
Fallback  : Convert official PDF → image (if pdf2image available)

HOW IT WORKS:
  lotterysambadresult.in uploads result images to WordPress.
  Image URL pattern:
    https://lotterysambadresult.in/wp-content/uploads/YYYY/MM/img_XXXX.webp
  We find the latest result image, download it, and save it
  to /images/ with an SEO-friendly filename.

REQUIREMENTS:
  pip install requests beautifulsoup4 Pillow
  (pdf2image optional — needs poppler-utils system package)

Author : Lottery Bot v2
"""

import re
import io
import time
import logging
import datetime
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    from PIL import Image
    PIL_OK = True
except ImportError:
    PIL_OK = False
    logging.warning("Pillow not installed — image conversion disabled")

try:
    from pdf2image import convert_from_path
    PDF2IMG_OK = True
except ImportError:
    PDF2IMG_OK = False

log = logging.getLogger("image_scraper")

# ── Constants ─────────────────────────────────────────────────────────
IMAGE_DIR = Path("images")
PDF_DIR   = Path("pdfs")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
}
TIMEOUT     = 20
MAX_IMG_MB  = 10
IMG_QUALITY = 85    # JPEG quality (1-95)
IMG_MAX_W   = 1200  # max width in pixels


def ensure_dirs():
    IMAGE_DIR.mkdir(exist_ok=True)
    PDF_DIR.mkdir(exist_ok=True)


def get_ist_now() -> datetime.datetime:
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)


def make_seo_filename(state: str, draw: str, date_str: str) -> str:
    """
    SEO-friendly filename:
    nagaland-state-lottery-sambad-result-today-8pm-2026-04-03
    """
    draw_slug  = draw.lower().replace(" ", "")
    state_slug = state.lower().replace("_", "-").replace(" ", "-")
    return f"{state_slug}-state-lottery-sambad-result-today-{draw_slug}-{date_str}"


def save_image(img_bytes: bytes, dest_path: Path) -> bool:
    """Convert and save image bytes as optimized JPEG."""
    if not PIL_OK:
        # Save raw without processing
        with open(dest_path, "wb") as f:
            f.write(img_bytes)
        log.info(f"Saved raw image: {dest_path} ({len(img_bytes)//1024} KB)")
        return True
    try:
        img = Image.open(io.BytesIO(img_bytes))
        # Convert RGBA / palette to RGB
        if img.mode in ("RGBA", "P", "LA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                bg.paste(img, mask=img.split()[3])
            else:
                bg.paste(img)
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        # Resize if too large
        if img.width > IMG_MAX_W:
            ratio = IMG_MAX_W / img.width
            img = img.resize((IMG_MAX_W, int(img.height * ratio)), Image.LANCZOS)
        img.save(str(dest_path), "JPEG", quality=IMG_QUALITY, optimize=True)
        log.info(f"✓ Image saved: {dest_path} ({dest_path.stat().st_size // 1024} KB)")
        return True
    except Exception as e:
        log.error(f"Image save failed: {e}")
        return False


def download_image(url: str, dest_path: Path) -> bool:
    """Download image from URL and save to dest_path."""
    if dest_path.exists() and dest_path.stat().st_size > 5000:
        log.info(f"Image already exists: {dest_path}")
        return True
    try:
        log.info(f"Downloading image: {url}")
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)
        r.raise_for_status()
        ct = r.headers.get("Content-Type", "")
        if not any(x in ct.lower() for x in ["image", "jpeg", "png", "webp", "octet"]):
            log.warning(f"Unexpected content-type: {ct} from {url}")
        chunks = []
        total  = 0
        for chunk in r.iter_content(8192):
            if chunk:
                chunks.append(chunk)
                total += len(chunk)
                if total > MAX_IMG_MB * 1024 * 1024:
                    log.warning("Image too large — aborting download")
                    return False
        img_bytes = b"".join(chunks)
        return save_image(img_bytes, dest_path)
    except requests.exceptions.RequestException as e:
        log.error(f"Download failed for {url}: {e}")
        return False


# ── SCRAPER 1: lotterysambadresult.in ────────────────────────────────

def scrape_lotterysambad_result(draw: str) -> str | None:
    """
    Scrape https://lotterysambadresult.in/ for the latest result image.

    This WordPress site uploads result images to:
      /wp-content/uploads/YYYY/MM/img_XXXXXXXX.webp

    The site has separate pages per draw:
      1PM: /nagaland-state-lottery-sambad-today-result-1-pm.html
      6PM: /nagaland-state-lottery-sambad-today-7-pm-result.html
      8PM: /lottery-sambad-today-result-08-00-pm.html

    Returns the image URL or None.
    """
    DRAW_URLS = {
        "1PM": "https://lotterysambadresult.in/nagaland-state-lottery-sambad-today-result-1-pm.html",
        "6PM": "https://lotterysambadresult.in/nagaland-state-lottery-sambad-today-7-pm-result.html",
        "8PM": "https://lotterysambadresult.in/lottery-sambad-today-result-08-00-pm.html",
    }

    # Also try the homepage
    URLS_TO_TRY = [
        DRAW_URLS.get(draw, "https://lotterysambadresult.in/"),
        "https://lotterysambadresult.in/",
    ]

    for url in URLS_TO_TRY:
        img_url = _extract_wp_image(url, draw)
        if img_url:
            return img_url
        time.sleep(1)

    return None


def _extract_wp_image(page_url: str, draw: str) -> str | None:
    """
    Extract the result image from a WordPress lottery page.
    Looks for:
      1. <img> with src containing wp-content/uploads
      2. <img> with class containing 'result' or 'lottery'
      3. Large images (width > 400px from width attribute)
      4. og:image meta tag
    """
    from bs4 import BeautifulSoup

    try:
        log.info(f"Scanning page: {page_url}")
        r = requests.get(page_url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        log.warning(f"Page fetch failed {page_url}: {e}")
        return None

    candidates = []

    # ── Strategy 1: og:image (most reliable on WordPress) ──
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        src = og["content"]
        if "wp-content/uploads" in src or any(x in src for x in ["result", "lottery", "sambad"]):
            log.info(f"Found og:image: {src}")
            candidates.append((10, src))

    # ── Strategy 2: img tags with wp-content/uploads ──
    for img in soup.find_all("img", src=True):
        src = img.get("src", "")
        if "wp-content/uploads" not in src:
            continue
        src = urljoin(page_url, src)

        score = 0
        # Prefer images with result-related names
        src_lower = src.lower()
        if any(x in src_lower for x in ["result", "lottery", "sambad", "dear", "img_"]):
            score += 5
        # Prefer webp / jpg (not thumbnails)
        if any(x in src_lower for x in [".webp", ".jpg", ".jpeg"]):
            score += 3
        # Prefer NOT tiny thumbnails (-150x150, -300x)
        if re.search(r'-\d{2,3}x\d{2,3}\.', src_lower):
            score -= 5
        # Width/height attributes hint at image size
        w = img.get("width", "0")
        try:
            w = int(str(w).replace("px", ""))
            if w > 400: score += 4
            if w > 700: score += 3
        except ValueError:
            pass
        # Prefer images near "result" headings
        parent = img.find_parent(["div", "section", "article"])
        if parent:
            txt = parent.get_text().lower()
            if any(x in txt for x in ["result", "draw", "prize", "winner"]):
                score += 3

        if score > 0:
            candidates.append((score, src))

    # ── Strategy 3: data-src (lazy loaded images) ──
    for img in soup.find_all("img", attrs={"data-src": True}):
        src = img.get("data-src", "")
        if "wp-content/uploads" in src:
            src = urljoin(page_url, src)
            candidates.append((2, src))
    for img in soup.find_all("img", attrs={"data-lazy-src": True}):
        src = img.get("data-lazy-src", "")
        if "wp-content/uploads" in src:
            src = urljoin(page_url, src)
            candidates.append((2, src))

    # ── Strategy 4: srcset attribute ──
    for img in soup.find_all("img", attrs={"srcset": True}):
        srcset = img.get("srcset", "")
        parts = [p.strip().split()[0] for p in srcset.split(",") if p.strip()]
        for src in parts:
            if "wp-content/uploads" in src and not re.search(r'-\d{2,3}x\d{2,3}\.', src):
                src = urljoin(page_url, src)
                candidates.append((1, src))

    if not candidates:
        log.warning(f"No image candidates found on {page_url}")
        return None

    # Sort by score, take best
    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score, best_url = candidates[0]
    log.info(f"Best image candidate (score={best_score}): {best_url}")
    return best_url


# ── SCRAPER 2: lotterysambad.one ─────────────────────────────────────

def scrape_lotterysambad_one(draw: str) -> str | None:
    """
    Scrape https://lotterysambad.one/ as alternate source.
    Similar WordPress pattern.
    """
    DRAW_URLS = {
        "1PM": "https://lotterysambad.one/",
        "6PM": "https://lotterysambad.one/",
        "8PM": "https://lotterysambad.one/",
    }
    url = DRAW_URLS.get(draw, "https://lotterysambad.one/")
    return _extract_wp_image(url, draw)


# ── FALLBACK: PDF → Image ─────────────────────────────────────────────

def pdf_to_image_fallback(pdf_path: Path, dest_path: Path) -> bool:
    """
    Convert first page of a PDF to image.
    Requires: pip install pdf2image + apt install poppler-utils
    """
    if not PDF2IMG_OK:
        log.warning("pdf2image not available — cannot convert PDF to image")
        return False
    if not pdf_path.exists():
        log.warning(f"PDF not found: {pdf_path}")
        return False
    if dest_path.exists() and dest_path.stat().st_size > 5000:
        return True
    try:
        pages = convert_from_path(str(pdf_path), dpi=150, first_page=1, last_page=1, fmt="jpeg")
        if pages:
            img = pages[0]
            if img.width > IMG_MAX_W:
                ratio = IMG_MAX_W / img.width
                img = img.resize((IMG_MAX_W, int(img.height * ratio)), Image.LANCZOS)
            img.save(str(dest_path), "JPEG", quality=IMG_QUALITY, optimize=True)
            log.info(f"✓ PDF→Image: {dest_path}")
            return True
    except Exception as e:
        log.error(f"PDF conversion failed: {e}")
    return False


# ── PUBLIC API ────────────────────────────────────────────────────────

def get_result_image(
    state:    str,
    draw:     str,
    date_str: str | None = None,
    pdf_path: Path | None = None,
) -> str:
    """
    Main entry point. Returns local image path (relative) or "" if all fail.

    Priority order:
      1. lotterysambadresult.in (most reliable, updates fastest)
      2. lotterysambad.one (fallback site)
      3. PDF → image conversion (if PDF already downloaded)

    Args:
        state:    "nagaland" | "kerala"
        draw:     "1PM" | "6PM" | "8PM" | "3PM"
        date_str: "YYYY-MM-DD" (defaults to today IST)
        pdf_path: Path to already-downloaded PDF (for fallback)

    Returns:
        Relative path to saved image like "images/nagaland-state-lottery-...jpg"
        or "" if image could not be obtained.
    """
    ensure_dirs()

    if date_str is None:
        date_str = get_ist_now().strftime("%Y-%m-%d")

    slug      = make_seo_filename(state, draw, date_str)
    dest_path = IMAGE_DIR / f"{slug}.jpg"

    # Already have it?
    if dest_path.exists() and dest_path.stat().st_size > 5000:
        log.info(f"Image already exists: {dest_path}")
        return str(dest_path).replace("\\", "/")

    # ── Source 1: lotterysambadresult.in ──
    if state == "nagaland":
        log.info(f"[Image] Trying lotterysambadresult.in for {draw}...")
        img_url = scrape_lotterysambad_result(draw)
        if img_url and download_image(img_url, dest_path):
            return str(dest_path).replace("\\", "/")
        time.sleep(2)

        # ── Source 2: lotterysambad.one ──
        log.info("[Image] Trying lotterysambad.one...")
        img_url = scrape_lotterysambad_one(draw)
        if img_url and download_image(img_url, dest_path):
            return str(dest_path).replace("\\", "/")

    # ── Source 3: PDF → image fallback ──
    if pdf_path and pdf_path.exists():
        log.info(f"[Image] Trying PDF→image conversion: {pdf_path}")
        if pdf_to_image_fallback(pdf_path, dest_path):
            return str(dest_path).replace("\\", "/")

    log.warning(f"[Image] All sources failed for {state} {draw} {date_str}")
    return ""


# ── STANDALONE TEST ───────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    draw = sys.argv[1] if len(sys.argv) > 1 else "8PM"
    print(f"\nTesting image scraper for Nagaland {draw}...\n")

    result = get_result_image("nagaland", draw)
    if result:
        print(f"\n✅ SUCCESS: {result}")
    else:
        print("\n❌ FAILED: No image obtained from any source")

    print("\nDone.")
