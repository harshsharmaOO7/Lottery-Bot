"""
parser.py — PDF Downloader & Record Builder v3
===============================================
Downloads official lottery PDFs and builds structured records.
"""

import logging
import datetime
import requests
from pathlib import Path

log = logging.getLogger("parser")

try:
    from pdf2image import convert_from_path
    from PIL import Image
    PDF2IMG_OK = True
except ImportError:
    PDF2IMG_OK = False

PDF_DIR   = Path("pdfs")
IMAGE_DIR = Path("images")
HEADERS   = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
TIMEOUT   = 30
MAX_MB    = 20


def ensure_dirs():
    PDF_DIR.mkdir(exist_ok=True)
    IMAGE_DIR.mkdir(exist_ok=True)


def get_ist_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)


def seo_filename(state: str, draw: str, date: str) -> str:
    """SEO-friendly slug: nagaland-state-lottery-sambad-result-today-8pm-2026-04-03"""
    return f"{state.lower().replace('_','-')}-state-lottery-sambad-result-today-{draw.lower()}-{date}"


def download_pdf(url: str, path: Path) -> bool:
    if path.exists() and path.stat().st_size > 1024:
        log.info(f"PDF cached: {path}")
        return True
    try:
        log.info(f"Downloading PDF: {url}")
        with requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True) as r:
            r.raise_for_status()
            size = 0
            with open(path, "wb") as f:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)
                        size += len(chunk)
                        if size > MAX_MB * 1024 * 1024:
                            path.unlink(missing_ok=True)
                            log.warning("PDF too large")
                            return False
        log.info(f"✓ PDF saved: {path} ({path.stat().st_size // 1024} KB)")
        return True
    except Exception as e:
        log.error(f"PDF download failed: {e}")
        path.unlink(missing_ok=True)
        return False


def pdf_to_image(pdf_path: Path, img_path: Path) -> bool:
    if not PDF2IMG_OK: return False
    if img_path.exists() and img_path.stat().st_size > 1024: return True
    try:
        pages = convert_from_path(str(pdf_path), dpi=150, first_page=1, last_page=1, fmt="jpeg")
        if pages:
            img = pages[0]
            if img.width > 1200:
                r = 1200 / img.width
                img = img.resize((1200, int(img.height * r)), Image.LANCZOS)
            img.save(str(img_path), "JPEG", quality=85, optimize=True)
            log.info(f"✓ PDF→Image: {img_path}")
            return True
    except Exception as e:
        log.error(f"PDF→Image failed: {e}")
    return False


def build_record(state: str, raw: dict, date_str: str | None = None) -> dict | None:
    ensure_dirs()
    if not date_str:
        date_str = get_ist_now().strftime("%Y-%m-%d")

    draw     = raw.get("draw", "1PM")
    pdf_url  = raw.get("pdf_url", "")
    source   = raw.get("source", "")
    verified = raw.get("verified", False)
    draw_name = raw.get("draw_name", f"{state.title()} {draw}")

    slug     = seo_filename(state, draw, date_str)
    pdf_path = PDF_DIR   / f"{slug}.pdf"
    img_path = IMAGE_DIR / f"{slug}.jpg"

    # Download PDF
    pdf_local = ""
    if pdf_url and download_pdf(pdf_url, pdf_path):
        pdf_local = str(pdf_path).replace("\\", "/")
        pdf_to_image(pdf_path, img_path)
    else:
        pdf_local = pdf_url  # fallback: use remote URL

    img_local = str(img_path).replace("\\", "/") if img_path.exists() else ""
    ts = get_ist_now().strftime("%Y-%m-%dT%H:%M:%S+05:30")

    return {
        "date":       date_str,
        "draw":       draw,
        "draw_name":  draw_name,
        "pdf":        pdf_local,
        "pdf_url":    pdf_url,
        "image":      img_local,
        "source":     source,
        "verified":   verified,
        "fetched_at": ts,
    }
