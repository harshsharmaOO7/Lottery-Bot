#!/usr/bin/env python3
"""
update_result.py — Manual results.json updater
================================================
Jab GitHub app se image upload karo tab ye script chalaao.
Ya GitHub Actions se automatically chalta hai.

Usage:
  python update_result.py --draw 8PM --date 2026-04-13
  python update_result.py --draw 1PM
  python update_result.py --draw all   (aaj ke saare draws scan kare images/ folder se)

images/ folder mein file naming convention:
  nagaland-1pm-2026-04-13.jpg
  nagaland-6pm-2026-04-13.jpg
  nagaland-8pm-2026-04-13.jpg
  kerala-3pm-2026-04-13.jpg
"""

import sys
import json
import argparse
import datetime
from pathlib import Path

RESULTS_FILE = Path("results.json")
IMAGE_DIR    = Path("images")
MAX_HISTORY  = 30

# Draw name schedules
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
    "3PM": {0:"Win-Win", 1:"Sthree Sakthi", 2:"Akshaya", 3:"Karunya Plus",
            4:"Nirmal",  5:"Karunya",        6:"Pournami"},
}

def get_ist():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

def ist_date():
    return get_ist().strftime("%Y-%m-%d")

def ist_ts():
    return get_ist().strftime("%Y-%m-%dT%H:%M:%S+05:30")

def get_draw_name(draw: str, date_str: str) -> str:
    """Get draw name based on day of week for given date."""
    try:
        d   = datetime.date.fromisoformat(date_str)
        dow = d.weekday()  # 0=Mon, 6=Sun
        return DRAW_NAMES.get(draw, {}).get(dow, f"Dear {draw}")
    except Exception:
        return f"Dear {draw}"

def find_image(draw: str, date_str: str) -> str:
    """
    images/ folder mein image dhundho.
    Expected filename: nagaland-8pm-2026-04-13.jpg
    Also accepts: nagaland-8pm-2026-04-13.png / .webp / .jpeg
    """
    if not IMAGE_DIR.exists():
        return ""

    draw_lower = draw.lower()
    state = "kerala" if draw == "3PM" else "nagaland"
    prefixes = [
        f"{state}-{draw_lower}-{date_str}",    # nagaland-8pm-2026-04-13
        f"{draw_lower}-{date_str}",             # 8pm-2026-04-13
        f"{state}-{draw_lower}",                # nagaland-8pm (fallback, no date)
    ]
    extensions = [".jpg", ".jpeg", ".png", ".webp"]

    for prefix in prefixes:
        for ext in extensions:
            p = IMAGE_DIR / (prefix + ext)
            if p.exists() and p.stat().st_size > 1000:
                return str(p).replace("\\", "/")

    # Fallback: any image with date + draw in name
    for f in sorted(IMAGE_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.suffix.lower() in [".jpg",".jpeg",".png",".webp"]:
            name = f.name.lower()
            if date_str in name and draw_lower in name:
                return str(f).replace("\\", "/")

    return ""

def load_results() -> dict:
    if RESULTS_FILE.exists():
        try:
            return json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"nagaland": [], "kerala": [], "last_updated": "", "total_records": 0}

def save_results(data: dict):
    tmp = RESULTS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(RESULTS_FILE)
    print(f"✓ results.json saved")

def update_draw(draw: str, date: str, results: dict) -> bool:
    """Add or update one draw in results.json. Returns True if changed."""
    state    = "kerala" if draw == "3PM" else "nagaland"
    img_path = find_image(draw, date)

    if not img_path:
        print(f"⚠  {draw}: No image found in images/ for date {date}")
        print(f"   Expected: images/{state}-{draw.lower()}-{date}.jpg")
        return False

    arr = results.setdefault(state, [])

    # Check if record already exists
    existing = next((r for r in arr if r.get("date")==date and r.get("draw")==draw), None)

    if existing:
        if existing.get("image") == img_path:
            print(f"ℹ  {draw}: No change (same image)")
            return False
        existing["image"]      = img_path
        existing["fetched_at"] = ist_ts()
        print(f"✓  {draw}: Updated image → {img_path}")
        return True

    # New record
    record = {
        "date":       date,
        "draw":       draw,
        "draw_name":  get_draw_name(draw, date),
        "image":      img_path,
        "pdf":        "",
        "source":     "manual",
        "verified":   True,
        "fetched_at": ist_ts(),
    }
    arr.insert(0, record)
    arr[:] = arr[:MAX_HISTORY]
    print(f"✓  {draw}: Added → {img_path} | {record['draw_name']}")
    return True

def scan_all(date: str, results: dict) -> bool:
    """Scan images/ folder for today's images and update all draws."""
    changed = False
    for draw in ["1PM", "6PM", "8PM", "3PM"]:
        if update_draw(draw, date, results):
            changed = True
    return changed

def main():
    p = argparse.ArgumentParser(description="Manual results.json updater")
    p.add_argument("--draw", default="all", help="1PM / 6PM / 8PM / 3PM / all")
    p.add_argument("--date", default=None,  help="YYYY-MM-DD (default: today IST)")
    args = p.parse_args()

    date = args.date or ist_date()
    print(f"\n{'='*48}")
    print(f"  update_result.py | Date: {date} | Draw: {args.draw}")
    print(f"{'='*48}\n")

    results = load_results()
    changed = False

    if args.draw == "all":
        changed = scan_all(date, results)
    elif args.draw in ("1PM","6PM","8PM","3PM"):
        changed = update_draw(args.draw, date, results)
    else:
        print(f"Unknown draw: {args.draw}")
        sys.exit(1)

    results["last_updated"]  = ist_ts()
    results["total_records"] = sum(len(results.get(s,[])) for s in ["nagaland","kerala"])
    save_results(results)

    print(f"\n{'='*48}")
    print("RESULTS.JSON STATUS:")
    for r in results.get("nagaland",[])[:5]:
        has = "✅" if r.get("image") else "❌"
        print(f"  {has} {r['date']} {r['draw']:3} | {r['draw_name']}")
        if r.get("image"):
            print(f"       → {r['image']}")
    print(f"{'='*48}\n")

    sys.exit(0 if changed else 0)

if __name__ == "__main__":
    main()
