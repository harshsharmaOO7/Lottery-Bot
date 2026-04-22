#!/usr/bin/env python3
"""
update_result.py
================
GitHub pe image upload hone ke baad ye automatically chalta hai.
images/ folder scan karta hai aur results.json update karta hai.

Image naming: nagaland-8pm-2026-04-22.jpg
              nagaland-6pm-2026-04-22.jpg
              nagaland-1pm-2026-04-22.jpg
"""
import json, datetime, sys, argparse
from pathlib import Path

RESULTS_FILE = Path("results.json")
IMAGE_DIR    = Path("images")
MAX_HISTORY  = 60

DRAW_NAMES = {
    "1PM": {0:"Dear Dwarka Morning",   1:"Dear Godavari Morning", 2:"Dear Indus Morning",
            3:"Dear Mahanadi Morning", 4:"Dear Meghna Morning",   5:"Dear Narmada Morning",
            6:"Dear Yamuna Morning"},
    "6PM": {0:"Dear Blitzen Evening",  1:"Dear Comet Evening",   2:"Dear Cupid Evening",
            3:"Dear Dancer Evening",   4:"Dear Dasher Evening",  5:"Dear Donner Evening",
            6:"Dear Vixen Evening"},
    "8PM": {0:"Dear Flamingo Evening", 1:"Dear Parrot Evening",  2:"Dear Eagle Evening",
            3:"Dear Falcon Evening",   4:"Dear Vulture Evening", 5:"Dear Ostrich Evening",
            6:"Dear Hawk Evening"},
}

def ist():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

def ist_date():
    return ist().strftime("%Y-%m-%d")

def ist_ts():
    return ist().strftime("%Y-%m-%dT%H:%M:%S+05:30")

def draw_name(draw, date_str):
    try:
        dow = datetime.date.fromisoformat(date_str).weekday()
        return DRAW_NAMES.get(draw, {}).get(dow, f"Nagaland {draw}")
    except:
        return f"Nagaland {draw}"

def load():
    if RESULTS_FILE.exists():
        try:
            return json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
        except:
            pass
    return {"nagaland": [], "kerala": [], "last_updated": "", "total_records": 0}

def save(data):
    tmp = RESULTS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(RESULTS_FILE)
    print(f"  ✓ results.json saved")

def find_image(draw, date_str):
    """images/ folder mein aaj ki image dhundho."""
    if not IMAGE_DIR.exists():
        return ""
    draw_l = draw.lower()
    # Try exact name first
    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        for name in [
            f"nagaland-{draw_l}-{date_str}{ext}",
            f"nagaland_{draw_l}_{date_str}{ext}",
            f"{draw_l}-{date_str}{ext}",
        ]:
            p = IMAGE_DIR / name
            if p.exists() and p.stat().st_size > 500:
                return str(p).replace("\\", "/")
    # Fallback: any file with date + draw in name (newest first)
    candidates = []
    for f in IMAGE_DIR.iterdir():
        if f.suffix.lower() in [".jpg",".jpeg",".png",".webp"]:
            n = f.name.lower()
            if date_str in n and draw_l in n:
                candidates.append(f)
    if candidates:
        candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return str(candidates[0]).replace("\\", "/")
    return ""

def scan_and_update(date_str, results):
    changed = False
    draws = ["1PM", "6PM", "8PM"]
    for draw in draws:
        img = find_image(draw, date_str)
        if not img:
            print(f"  ⚠  {draw}: No image found for {date_str}")
            print(f"     Expected: images/nagaland-{draw.lower()}-{date_str}.jpg")
            continue
        arr = results.setdefault("nagaland", [])
        # Update existing or add new
        existing = next((r for r in arr if r.get("date")==date_str and r.get("draw")==draw), None)
        if existing:
            if existing.get("image") == img:
                print(f"  ℹ  {draw}: No change")
                continue
            existing["image"] = img
            existing["fetched_at"] = ist_ts()
            print(f"  ✓  {draw}: Updated → {img}")
        else:
            arr.insert(0, {
                "date": date_str,
                "draw": draw,
                "draw_name": draw_name(draw, date_str),
                "image": img,
                "pdf": "",
                "source": "manual",
                "verified": True,
                "fetched_at": ist_ts(),
            })
            arr[:] = arr[:MAX_HISTORY]
            print(f"  ✓  {draw}: Added → {img} | {draw_name(draw, date_str)}")
        changed = True
    return changed

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=None)
    args = p.parse_args()
    date = args.date or ist_date()
    print(f"\n=== update_result.py | {date} ===")
    results = load()
    changed = scan_and_update(date, results)
    results["last_updated"]  = ist_ts()
    results["total_records"] = sum(len(results.get(s,[])) for s in ["nagaland","kerala"])
    save(results)
    print("\nStatus:")
    for r in results.get("nagaland",[])[:6]:
        print(f"  {'✅' if r.get('image') else '❌'} {r['date']} {r['draw']:3} | {r['draw_name']}")
    sys.exit(0)

if __name__ == "__main__":
    main()
