#!/usr/bin/env python3
"""
bot.py — Lottery Result Automation Bot v3
==========================================
Fixed: date not updating (IST-aware date comparison)
New:   image scraping from lotterysambadresult.in
New:   sitemap.xml auto-generation
New:   per-state PDF download + image conversion

Usage:
    python bot.py                        # auto-detect draw
    python bot.py --draw 8PM            # force draw
    python bot.py --draw 8PM --date 2026-04-03
    python bot.py --state nagaland       # single state
    python bot.py --skip-image           # skip image scraping
"""

import sys
import json
import logging
import argparse
import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from scraper       import get_nagaland_result, get_kerala_result
from parser        import build_record
from image_scraper import get_result_image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("bot")

# ── Config ────────────────────────────────────────────────────────────
RESULTS_FILE    = Path("results.json")
SITEMAP_FILE    = Path("sitemap.xml")
MAX_HISTORY     = 30
STATES_ENABLED  = ["nagaland", "kerala"]

# ← UPDATE → Your GitHub Pages URL
SITE_BASE = "https://harshsharmaoo7.github.io/Lottery-Bot/"

SITE_PAGES = [
    ("index.html",                                 "daily",  "1.0"),
    ("nagaland-lottery-result-today-1pm.html",    "daily",  "0.9"),
    ("nagaland-lottery-result-today-6pm.html",    "daily",  "0.9"),
    ("nagaland-lottery-result-today-8pm.html",    "daily",  "0.9"),
    ("kerala-lottery-result-today.html",           "daily",  "0.9"),
    ("archive.html",                               "weekly", "0.7"),
    ("about.html",                                 "monthly","0.5"),
    ("disclaimer.html",                            "monthly","0.3"),
]


# ── IST helpers ───────────────────────────────────────────────────────

def get_ist_now() -> datetime.datetime:
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)


def get_ist_date() -> str:
    """Return today's date string in IST (fixes the date-not-updating bug)."""
    return get_ist_now().strftime("%Y-%m-%d")


def get_ist_timestamp() -> str:
    return get_ist_now().strftime("%Y-%m-%dT%H:%M:%S+05:30")


def detect_draw() -> str:
    """Auto-detect current draw from IST clock."""
    h = get_ist_now().hour
    if h < 14:      return "1PM"
    elif h < 19:    return "6PM"
    else:           return "8PM"


# ── results.json helpers ──────────────────────────────────────────────

def load_results() -> dict:
    if RESULTS_FILE.exists():
        try:
            with open(RESULTS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Corrupted results.json: {e} — starting fresh")
    return {s: [] for s in STATES_ENABLED} | {"last_updated": "", "total_records": 0}


def save_results(data: dict):
    tmp = RESULTS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(RESULTS_FILE)
    log.info(f"✓ results.json saved ({RESULTS_FILE.stat().st_size} bytes)")


def is_duplicate(lst: list, rec: dict) -> bool:
    """Check if date+draw already exists."""
    for r in lst:
        if r.get("date") == rec["date"] and r.get("draw") == rec["draw"]:
            log.info(f"Duplicate: {rec['date']} {rec['draw']} — skip")
            return True
    return False


def prepend(lst: list, rec: dict) -> list:
    """Add newest first, trim to MAX_HISTORY."""
    return ([rec] + lst)[:MAX_HISTORY]


# ── Sitemap generator ─────────────────────────────────────────────────

def generate_sitemap():
    """Auto-generate sitemap.xml with today's lastmod."""
    root = ET.Element("urlset")
    root.set("xmlns", "https://www.sitemaps.org/schemas/sitemap/0.9")
    today = get_ist_date()

    for page, freq, pri in SITE_PAGES:
        url = ET.SubElement(root, "url")
        ET.SubElement(url, "loc").text = SITE_BASE + page
        ET.SubElement(url, "lastmod").text = today
        ET.SubElement(url, "changefreq").text = freq
        ET.SubElement(url, "priority").text = pri

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    with open(SITEMAP_FILE, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        tree.write(f, encoding="utf-8", xml_declaration=False)

    log.info(f"✓ sitemap.xml updated ({len(SITE_PAGES)} pages)")


# ── State runners ─────────────────────────────────────────────────────

def run_nagaland(draw: str, date_str: str, results: dict, skip_image: bool) -> bool:
    log.info(f"━━ Nagaland {draw} ━━")

    # 1. Scrape PDF metadata
    raw = get_nagaland_result(draw)
    if not raw:
        log.warning("No PDF data from any Nagaland source")
        return False

    # 2. Build record (downloads PDF, converts to image via pdf2image)
    record = build_record("nagaland", raw, date_str)
    if not record:
        log.warning("Record build failed")
        return False

    # 3. Scrape result image (from lotterysambadresult.in)
    if not skip_image:
        pdf_path_str = record.get("pdf", "")
        pdf_path = Path(pdf_path_str) if pdf_path_str and not pdf_path_str.startswith("http") else None

        img_path = get_result_image(
            state    = "nagaland",
            draw     = draw,
            date_str = date_str,
            pdf_path = pdf_path,
        )
        if img_path:
            record["image"] = img_path
            log.info(f"Image: {img_path}")
        else:
            log.warning("No image obtained — result will show without image")

    # 4. Duplicate check + insert
    lst = results.setdefault("nagaland", [])
    if is_duplicate(lst, record):
        return False

    results["nagaland"] = prepend(lst, record)
    log.info(f"✓ Nagaland {draw} added | date={record['date']}")
    return True


def run_kerala(date_str: str, results: dict, skip_image: bool) -> bool:
    draw = "3PM"
    log.info(f"━━ Kerala {draw} ━━")

    raw = get_kerala_result(draw)
    if not raw:
        log.warning("No PDF data from any Kerala source")
        return False

    record = build_record("kerala", raw, date_str)
    if not record:
        return False

    # Kerala doesn't have images on Nagaland sambad sites — use PDF fallback only
    if not skip_image and not record.get("image"):
        pdf_path_str = record.get("pdf", "")
        pdf_path = Path(pdf_path_str) if pdf_path_str and not pdf_path_str.startswith("http") else None
        if pdf_path and pdf_path.exists():
            from image_scraper import pdf_to_image_fallback, make_seo_filename, IMAGE_DIR
            slug = make_seo_filename("kerala", draw, date_str)
            dest = IMAGE_DIR / f"{slug}.jpg"
            if pdf_to_image_fallback(pdf_path, dest):
                record["image"] = str(dest).replace("\\", "/")

    lst = results.setdefault("kerala", [])
    if is_duplicate(lst, record):
        return False

    results["kerala"] = prepend(lst, record)
    log.info(f"✓ Kerala {draw} added | date={record['date']}")
    return True


# ── Main ──────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Lottery Bot v3")
    p.add_argument("--draw",       choices=["1PM","6PM","8PM","3PM"], default=None)
    p.add_argument("--state",      choices=STATES_ENABLED + ["all"], default="all")
    p.add_argument("--date",       default=None, help="YYYY-MM-DD")
    p.add_argument("--skip-image", action="store_true", help="Skip image scraping")
    args = p.parse_args()

    # ── Date (IST-aware — fixes the date not updating bug) ──
    date_str = args.date or get_ist_date()

    # ── Draw ──
    draw = args.draw or detect_draw()

    log.info("=" * 60)
    log.info(f"  Lottery Bot v3 | IST Date: {date_str} | Draw: {draw}")
    log.info(f"  States: {args.state} | Skip image: {args.skip_image}")
    log.info("=" * 60)

    results     = load_results()
    any_updated = False
    states      = STATES_ENABLED if args.state == "all" else [args.state]

    for state in states:
        if state == "nagaland":
            if run_nagaland(draw, date_str, results, args.skip_image):
                any_updated = True
        elif state == "kerala":
            if run_kerala(date_str, results, args.skip_image):
                any_updated = True

    # Always update metadata + save
    results["last_updated"]  = get_ist_timestamp()
    results["total_records"] = sum(len(results.get(s, [])) for s in STATES_ENABLED)
    save_results(results)

    # Always regenerate sitemap (updates lastmod daily)
    generate_sitemap()

    # Summary
    log.info("=" * 60)
    if any_updated:
        log.info("✅ New results saved!")
        for st in states:
            arr = results.get(st, [])
            if arr:
                r = arr[0]
                log.info(f"  {st.upper()}: {r['date']} {r['draw']} | "
                         f"PDF={bool(r.get('pdf'))} | Image={bool(r.get('image'))}")
    else:
        log.info("ℹ️  No new data — DB already up to date")
    log.info(f"  Total records: {results['total_records']}")
    log.info(f"  Last updated:  {results['last_updated']}")
    log.info("=" * 60)

    sys.exit(0)


if __name__ == "__main__":
    main()
