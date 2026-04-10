#!/usr/bin/env python3
"""
check.py — Debug Tool
=====================
Ek command se sab check karo:
  python check.py          → Full check (all draws + image)
  python check.py --quick  → Sirf JSON + image URL (no download)
  python check.py --draw 8PM

Output:
  ✅ = Working
  ⚠️  = Warning (partial)
  ❌ = Failed
"""
import sys
import json
import datetime
import argparse
import requests
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# ── CONFIG — apna URL daalo ──────────────────────────
GITHUB_PAGES_JSON = "https://harshsharmaoo7.github.io/Lottery-Bot/results.json"
LOCAL_JSON        = "results.json"  # local test ke liye

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}

DRAW_PAGES_SITE1 = {
    "1PM": "https://lotterysambadresult.in/nagaland-state-lottery-sambad-today-result-1-pm.html",
    "6PM": "https://lotterysambadresult.in/nagaland-state-lottery-sambad-today-7-pm-result.html",
    "8PM": "https://lotterysambadresult.in/lottery-sambad-today-result-08-00-pm.html",
}
DRAW_PAGES_SITE2 = {
    "1PM": "https://lotterysambad.one/nagaland-state-lottery-result-1-pm/",
    "6PM": "https://lotterysambad.one/nagaland-state-lottery-result-6-pm/",
    "8PM": "https://lotterysambad.one/nagaland-state-lottery-result-8-pm/",
}

def ist_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

def ist_date():
    return ist_now().strftime("%Y-%m-%d")

def header(text):
    print(f"\n{'═'*52}")
    print(f"  {text}")
    print(f"{'═'*52}")

def ok(msg):    print(f"  ✅  {msg}")
def warn(msg):  print(f"  ⚠️   {msg}")
def fail(msg):  print(f"  ❌  {msg}")
def info(msg):  print(f"  ℹ️   {msg}")

# ── 1. results.json check ────────────────────────────────────────────
def check_json():
    header("1. results.json Check")

    # Local file
    local = Path(LOCAL_JSON)
    if local.exists():
        try:
            data = json.loads(local.read_text())
            ok(f"Local results.json found ({local.stat().st_size} bytes)")

            nagaland = data.get("nagaland", [])
            kerala   = data.get("kerala", [])
            total    = data.get("total_records", 0)
            updated  = data.get("last_updated", "N/A")

            info(f"Last updated : {updated}")
            info(f"Total records: {total}")
            info(f"Nagaland entries: {len(nagaland)}")
            info(f"Kerala entries  : {len(kerala)}")

            today = ist_date()
            print()

            # Check each draw
            for draw in ["1PM", "6PM", "8PM"]:
                rec = next((r for r in nagaland if r.get("draw") == draw), None)
                if not rec:
                    warn(f"Nagaland {draw}: No record found")
                    continue

                rec_date = rec.get("date", "")
                if rec_date == today:
                    ok(f"Nagaland {draw}: TODAY's result ✓ — {rec.get('draw_name','')}")
                else:
                    warn(f"Nagaland {draw}: Old result ({rec_date}) — today is {today}")

                # Check PDF
                pdf = rec.get("pdf", "") or rec.get("pdf_url", "")
                if pdf:
                    ok(f"  PDF : {pdf[:60]}...")
                else:
                    fail(f"  PDF : Missing!")

                # Check image
                img = rec.get("image", "")
                if img:
                    ok(f"  IMG : {img[:60]}...")
                else:
                    warn(f"  IMG : Missing (will show PDF only)")

        except json.JSONDecodeError as e:
            fail(f"results.json is corrupted: {e}")
    else:
        warn("Local results.json not found — checking GitHub Pages...")

    # GitHub Pages JSON
    print()
    info("Checking GitHub Pages JSON...")
    try:
        r = requests.get(
            GITHUB_PAGES_JSON + f"?v={ist_now().timestamp():.0f}",
            headers=HEADERS, timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            ok(f"GitHub Pages JSON reachable ({len(r.content)} bytes)")
            nagaland = data.get("nagaland", [])
            if nagaland:
                latest = nagaland[0]
                ok(f"Latest: {latest.get('date')} {latest.get('draw')} — {latest.get('draw_name')}")
                if latest.get("date") == ist_date():
                    ok("Today's result is LIVE on GitHub Pages!")
                else:
                    warn(f"GitHub Pages shows old result: {latest.get('date')}")
        elif r.status_code == 404:
            fail("GitHub Pages JSON not found (404) — site not deployed yet?")
        else:
            fail(f"GitHub Pages returned HTTP {r.status_code}")
    except requests.exceptions.ConnectionError:
        fail("Cannot reach GitHub Pages — check internet or site URL")
    except Exception as e:
        fail(f"GitHub Pages error: {e}")

# ── 2. Image source check ────────────────────────────────────────────
def check_image_sources(draw="8PM", quick=False):
    header(f"2. Image Source Check — {draw}")

    # Site 1
    info("Checking lotterysambadresult.in...")
    url1 = DRAW_PAGES_SITE1.get(draw)
    try:
        r = requests.get(url1, headers=HEADERS, timeout=12)
        if r.status_code == 200:
            ok(f"Page reachable: {url1}")
            soup = BeautifulSoup(r.text, "html.parser")

            # Find figure image
            fig = soup.find("figure", class_=lambda c: c and "aligncenter" in c and "size-full" in c)
            if fig:
                img = fig.find("img")
                if img:
                    src = img.get("src", "")
                    alt = img.get("alt", "")
                    ok(f"Found image in <figure>!")
                    info(f"URL : {src}")
                    info(f"Alt : {alt}")

                    # Check if today's date in alt
                    n = ist_now()
                    months = ["January","February","March","April","May","June",
                              "July","August","September","October","November","December"]
                    today_str = f"{n.day}-{months[n.month-1]}-{n.year}"
                    if today_str.lower() in alt.lower():
                        ok(f"Date match! '{today_str}' found in alt text ✓")
                    else:
                        warn(f"Date mismatch in alt. Expected '{today_str}', got: {alt}")

                    if not quick:
                        # Try downloading
                        info("Testing download...")
                        r2 = requests.get(src, headers={**HEADERS, "Referer": url1}, timeout=15, stream=True)
                        if r2.status_code == 200:
                            ct = r2.headers.get("Content-Type", "")
                            size = int(r2.headers.get("Content-Length", 0))
                            ok(f"Download OK! Type={ct} Size={size//1024}KB")
                        else:
                            fail(f"Download failed: HTTP {r2.status_code}")
                else:
                    warn("Figure found but no <img> inside")
            else:
                # Try fetchpriority
                imgs = soup.find_all("img", attrs={"fetchpriority": "high"})
                wp_imgs = [i for i in imgs if "wp-content/uploads" in i.get("src","")]
                if wp_imgs:
                    warn(f"No <figure> found, but {len(wp_imgs)} fetchpriority img(s) found")
                    info(f"First: {wp_imgs[0].get('src','')[:70]}")
                else:
                    # Try og:image
                    og = soup.find("meta", property="og:image")
                    if og and og.get("content"):
                        warn(f"No figure img. og:image fallback: {og['content'][:70]}")
                    else:
                        fail("No result image found on page!")
        else:
            fail(f"Site1 page returned HTTP {r.status_code}")
    except Exception as e:
        fail(f"Site1 error: {e}")

    print()

    # Site 2
    info("Checking lotterysambad.one...")
    url2 = DRAW_PAGES_SITE2.get(draw)
    try:
        r = requests.get(url2, headers=HEADERS, timeout=12)
        if r.status_code == 200:
            ok(f"Page reachable: {url2}")
            soup = BeautifulSoup(r.text, "html.parser")

            # og:image (Yoast sets this reliably)
            og = soup.find("meta", property="og:image")
            if og and og.get("content"):
                src = og["content"]
                ok(f"og:image found: {src[:70]}")
                if not quick:
                    r2 = requests.get(src, headers={**HEADERS, "Referer": url2}, timeout=15, stream=True)
                    if r2.status_code == 200:
                        ok(f"Download OK! Size={len(r2.content)//1024}KB")
                    else:
                        fail(f"Download failed: HTTP {r2.status_code}")
            else:
                fail("No og:image meta tag found!")
        else:
            fail(f"Site2 page returned HTTP {r.status_code}")
    except Exception as e:
        fail(f"Site2 error: {e}")

# ── 3. GitHub Actions check ──────────────────────────────────────────
def check_actions():
    header("3. GitHub Actions Status")
    info("Check manually at:")
    info("→ https://github.com/harshsharmaOO7/Lottery-Bot/actions")
    print()

    now_ist = ist_now()
    h = now_ist.hour

    if h < 13:
        info(f"Current IST: {now_ist.strftime('%H:%M')} — Waiting for 1PM draw")
    elif h < 14:
        ok(f"Current IST: {now_ist.strftime('%H:%M')} — 1PM draw time! Bot should run soon")
    elif h < 18:
        info(f"Current IST: {now_ist.strftime('%H:%M')} — Waiting for 6PM draw")
    elif h < 19:
        ok(f"Current IST: {now_ist.strftime('%H:%M')} — 6PM draw time! Bot should run soon")
    elif h < 20:
        info(f"Current IST: {now_ist.strftime('%H:%M')} — Waiting for 8PM draw")
    elif h < 21:
        ok(f"Current IST: {now_ist.strftime('%H:%M')} — 8PM draw time! Bot should run soon")
    else:
        info(f"Current IST: {now_ist.strftime('%H:%M')} — All draws done for today")

    print()
    info("Expected bot run times (IST):")
    info("  1:05 PM — After 1PM draw")
    info("  6:05 PM — After 6PM draw")
    info("  8:10 PM — After 8PM draw")

# ── 4. Image folder check ────────────────────────────────────────────
def check_local_files():
    header("4. Local Files Check")

    pdfs = list(Path("pdfs").glob("*.pdf")) if Path("pdfs").exists() else []
    imgs = list(Path("images").glob("*.jpg")) if Path("images").exists() else []

    today = ist_date()
    today_pdfs = [f for f in pdfs if today in f.name]
    today_imgs = [f for f in imgs if today in f.name]

    info(f"Total PDFs in /pdfs/   : {len(pdfs)}")
    info(f"Total Images in /images/: {len(imgs)}")
    print()

    if today_pdfs:
        ok(f"Today's PDFs ({len(today_pdfs)}):")
        for f in today_pdfs:
            print(f"     {f.name} ({f.stat().st_size//1024}KB)")
    else:
        warn(f"No PDFs for today ({today}) in /pdfs/")

    if today_imgs:
        ok(f"Today's Images ({len(today_imgs)}):")
        for f in today_imgs:
            print(f"     {f.name} ({f.stat().st_size//1024}KB)")
    else:
        warn(f"No images for today ({today}) in /images/")

# ── MAIN ─────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="Lottery Bot Debug Checker")
    p.add_argument("--draw",  default="8PM", choices=["1PM","6PM","8PM"])
    p.add_argument("--quick", action="store_true", help="Skip downloads")
    p.add_argument("--json-only",  action="store_true")
    p.add_argument("--image-only", action="store_true")
    args = p.parse_args()

    print(f"\n🔍 Lottery Bot Debug Check")
    print(f"   IST Time : {ist_now().strftime('%Y-%m-%d %H:%M:%S')} IST")
    print(f"   IST Date : {ist_date()}")

    if args.json_only:
        check_json()
    elif args.image_only:
        check_image_sources(args.draw, args.quick)
    else:
        check_json()
        check_image_sources(args.draw, args.quick)
        check_local_files()
        check_actions()

    print(f"\n{'═'*52}\n")

if __name__ == "__main__":
    main()
