"""
parser.py — Result Data Builder
=================================
Builds structured result records from scraped raw data.
Does NOT extract or process lottery numbers.

Author : Lottery Bot
Version: 2.0.0
"""

import os
import logging
import datetime
import requests
from pathlib import Path
from urllib.parse import urlparse

log = logging.getLogger("parser")

# Attempt PDF-to-image conversion (optional — skip if not installed)
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    log.warning("pdf2image not installed — image previews disabled (pip install pdf2image)")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ── Constants ─────────────────────────────────────────────────────────
PDF_DIR   = Path("pdfs")
IMAGE_DIR = Path("images")
HEADERS   = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
TIMEOUT   = 30
MAX_PDF_SIZE_MB = 20   # reject files larger than this


def ensure_dirs():
    """Create required directories if they don't exist."""
    PDF_DIR.mkdir(exist_ok=True)
    IMAGE_DIR.mkdir(exist_ok=True)


def get_ist_now() -> datetime.datetime:
    """Return current datetime in IST."""
    utc = datetime.datetime.utcnow()
    return utc + datetime.timedelta(hours=5, minutes=30)


def make_filename(state: str, draw: str, date_str: str) -> str:
    """Generate a clean filename slug."""
    draw_slug = draw.lower().replace("pm", "pm").replace(" ", "")
    state_slug = state.lower().replace(" ", "_")
    return f"{date_str}-{state_slug}-{draw_slug}"


def download_pdf(pdf_url: str, dest_path: Path) -> bool:
    """
    Download a PDF from url → dest_path.
    Returns True on success, False on failure.
    Skips download if file already exists and is non-empty.
    """
    if dest_path.exists() and dest_path.stat().st_size > 1024:
        log.info(f"PDF already exists: {dest_path}")
        return True

    try:
        log.info(f"Downloading PDF: {pdf_url}")
        with requests.get(
            pdf_url,
            headers=HEADERS,
            timeout=TIMEOUT,
            stream=True
        ) as r:
            r.raise_for_status()

            # Content type check
            ct = r.headers.get("Content-Type", "")
            if "pdf" not in ct.lower() and "octet-stream" not in ct.lower():
                log.warning(f"Unexpected Content-Type: {ct} for {pdf_url}")

            # Size check
            content_length = int(r.headers.get("Content-Length", 0))
            if content_length > MAX_PDF_SIZE_MB * 1024 * 1024:
                log.warning(f"PDF too large ({content_length} bytes) — skipping")
                return False

            with open(dest_path, "wb") as f:
                downloaded = 0
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if downloaded > MAX_PDF_SIZE_MB * 1024 * 1024:
                            log.warning("PDF exceeded max size limit mid-download")
                            f.close()
                            dest_path.unlink(missing_ok=True)
                            return False

        size_kb = dest_path.stat().st_size // 1024
        log.info(f"✓ PDF saved: {dest_path} ({size_kb} KB)")
        return True

    except requests.exceptions.HTTPError as e:
        log.error(f"HTTP error downloading PDF: {e}")
    except requests.exceptions.ConnectionError:
        log.error(f"Connection error downloading PDF from {pdf_url}")
    except requests.exceptions.Timeout:
        log.error(f"Timeout downloading PDF from {pdf_url}")
    except Exception as e:
        log.error(f"Unexpected error downloading PDF: {e}")

    # Clean up partial file
    if dest_path.exists():
        dest_path.unlink(missing_ok=True)
    return False


def pdf_to_image(pdf_path: Path, image_path: Path, dpi: int = 150) -> bool:
    """
    Convert first page of PDF to a JPEG image preview.
    Returns True on success, False if unavailable/failed.
    """
    if not PDF2IMAGE_AVAILABLE:
        return False

    if image_path.exists() and image_path.stat().st_size > 1024:
        log.info(f"Image already exists: {image_path}")
        return True

    try:
        log.info(f"Converting PDF → image: {pdf_path}")
        pages = convert_from_path(
            str(pdf_path),
            dpi=dpi,
            first_page=1,
            last_page=1,
            fmt="jpeg",
        )
        if pages:
            img = pages[0]
            # Resize to max width 1200px to save space
            if img.width > 1200:
                ratio = 1200 / img.width
                new_h = int(img.height * ratio)
                img = img.resize((1200, new_h), Image.LANCZOS)
            img.save(str(image_path), "JPEG", quality=85, optimize=True)
            size_kb = image_path.stat().st_size // 1024
            log.info(f"✓ Image saved: {image_path} ({size_kb} KB)")
            return True
    except Exception as e:
        log.error(f"PDF→image conversion failed: {e}")

    return False


def build_record(
    state: str,
    raw: dict,
    date_str: str | None = None,
) -> dict | None:
    """
    Build a complete structured result record:
    - Downloads the PDF
    - Converts PDF to image (if possible)
    - Returns a record dict ready for results.json

    Args:
        state   : "nagaland" | "kerala" | ...
        raw     : output from scraper.get_*_result()
        date_str: ISO date string, defaults to today IST

    Returns: record dict or None if PDF could not be downloaded
    """
    ensure_dirs()

    if date_str is None:
        date_str = get_ist_now().strftime("%Y-%m-%d")

    draw      = raw.get("draw", "1PM")
    pdf_url   = raw.get("pdf_url", "")
    source    = raw.get("source", "")
    verified  = raw.get("verified", False)
    draw_name = raw.get("draw_name", f"{state.title()} {draw}")

    # Generate paths
    slug       = make_filename(state, draw, date_str)
    pdf_path   = PDF_DIR   / f"{slug}.pdf"
    image_path = IMAGE_DIR / f"{slug}.jpg"

    # Download PDF
    pdf_downloaded = False
    if pdf_url:
        pdf_downloaded = download_pdf(pdf_url, pdf_path)

    if not pdf_downloaded:
        log.warning(f"No PDF available for {state} {draw} on {date_str}")
        # Still create a record without local PDF (use remote URL as fallback)
        pdf_local = pdf_url   # point to original URL if local download failed
    else:
        pdf_local = str(pdf_path).replace("\\", "/")

        # Convert to image
        pdf_to_image(pdf_path, image_path)

    # Image path (relative for GitHub raw serving)
    image_local = (
        str(image_path).replace("\\", "/")
        if image_path.exists()
        else ""
    )

    # IST timestamp
    ist_now = get_ist_now()
    timestamp = ist_now.strftime("%Y-%m-%dT%H:%M:%S+05:30")

    return {
        "date":        date_str,
        "draw":        draw,
        "draw_name":   draw_name,
        "pdf":         pdf_local,
        "pdf_url":     pdf_url,           # original remote URL
        "image":       image_local,
        "source":      source,
        "verified":    verified,
        "fetched_at":  timestamp,
    }
