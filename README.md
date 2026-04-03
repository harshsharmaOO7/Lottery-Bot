# 🎱 Lottery Sambad Result Bot

**Fully automated** lottery result website powered by GitHub Actions + GitHub Pages.
Fetches official PDF results 3× daily and displays them on a fast static website.

[![Bot Status](https://github.com/harshsharmaOO7/Lottery-Bot/actions/workflows/main.yml/badge.svg)](https://github.com/harshsharmaOO7/Lottery-Bot/actions)

---

## 🌐 Live Site

> **https://harshsharmaoo7.github.io/Lottery-Bot/**

---

## 📂 Project Structure

```
Lottery-Bot/
├── index.html              ← Frontend (GitHub Pages)
├── results.json            ← Auto-updated result database
├── sources.json            ← Scrape source URLs (config)
├── requirements.txt        ← Python dependencies
│
├── bot.py                  ← Main orchestrator (entry point)
├── scraper.py              ← Official site scrapers
├── parser.py               ← PDF downloader + record builder
│
├── pdfs/                   ← Downloaded official PDFs (auto-created)
│   └── 2026-04-03-nagaland-8pm.pdf
│
├── images/                 ← PDF preview images (auto-created)
│   └── 2026-04-03-nagaland-8pm.jpg
│
└── .github/
    └── workflows/
        └── main.yml        ← GitHub Actions (runs 3× daily IST)
```

---

## ⚙️ GitHub Actions Schedule

| Cron (UTC) | IST Time | Draw |
|---|---|---|
| `35 7 * * *`  | 1:05 PM IST  | 1PM Nagaland |
| `35 12 * * *` | 6:05 PM IST  | 6PM Nagaland |
| `40 14 * * *` | 8:10 PM IST  | 8PM Nagaland |

---

## 🚀 Deploy Guide (Step by Step)

### Step 1 — Fork / Clone

```bash
git clone https://github.com/harshsharmaOO7/Lottery-Bot.git
cd Lottery-Bot
```

### Step 2 — Enable GitHub Pages

1. Go to your repo → **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: **main** | Folder: **/ (root)**
4. Click **Save**

Your site will be live at:
`https://YOUR_USERNAME.github.io/Lottery-Bot/`

### Step 3 — Update URLs in index.html

Open `index.html` and update these two lines at the top of `<script>`:

```javascript
const JSON_URL  = 'results.json';  // ← keep as-is for GitHub Pages
const RAW_BASE  = 'https://raw.githubusercontent.com/YOUR_USERNAME/Lottery-Bot/main/';
```

Also update the canonical URL in `<head>`:
```html
<link rel="canonical" href="https://YOUR_USERNAME.github.io/Lottery-Bot/">
```

### Step 4 — Test bot locally

```bash
# Install dependencies
pip install -r requirements.txt

# Install poppler (for PDF→image):
# Ubuntu/Debian: sudo apt-get install poppler-utils
# macOS:         brew install poppler
# Windows:       Download from https://poppler.freedesktop.org/

# Run bot (auto-detects draw from current IST time)
python bot.py

# Run for specific draw
python bot.py --draw 8PM

# Run for specific state only
python bot.py --state nagaland --draw 1PM

# Backfill a specific date
python bot.py --date 2026-04-02 --draw 6PM
```

### Step 5 — Push to GitHub

```bash
git add .
git commit -m "Initial setup"
git push origin main
```

GitHub Actions will now run automatically on schedule.

---

## 📊 results.json Format

```json
{
  "nagaland": [
    {
      "date":       "2026-04-03",
      "draw":       "8PM",
      "draw_name":  "Dear Pelican Night",
      "pdf":        "pdfs/2026-04-03-nagaland-8pm.pdf",
      "pdf_url":    "https://original-source-url.pdf",
      "image":      "images/2026-04-03-nagaland-8pm.jpg",
      "source":     "https://www.nagalandlotteries.com/results.php",
      "verified":   true,
      "fetched_at": "2026-04-03T20:05:30+05:30"
    }
  ],
  "kerala": [ ... ],
  "last_updated":  "2026-04-03T20:05:30+05:30",
  "total_records": 20
}
```

**Array order**: newest first. Max 30 entries per state (configurable in `bot.py`).

---

## 🔧 Configuration

### Adjust max history kept (`bot.py`):
```python
MAX_HISTORY = 30   # ← change to keep more/fewer entries
```

### Add more states (`bot.py`):
```python
STATES_ENABLED = ["nagaland", "kerala"]  # ← add "sikkim", "west_bengal" etc.
```

### Add sources (`sources.json`):
```json
{
  "nagaland": {
    "official": ["https://www.nagalandlotteries.com/results.php"],
    "mirrors":  ["https://lotterysambadresult.in/"]
  }
}
```

---

## 💰 AdSense Integration

After your site is approved by Google AdSense:

1. Uncomment the AdSense script in `index.html`:
```html
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXX" crossorigin="anonymous"></script>
```

2. Replace the `<div class="ad-ph ...">` placeholders with your `<ins>` tags.

---

## 🔒 Important Rules

- ✅ Displays official PDFs only — no number extraction
- ✅ Uses official government sources as primary
- ✅ Respects robots.txt and uses proper User-Agent
- ✅ 8-second timeout + retry logic prevents hanging
- ✅ Duplicate check prevents double entries
- ❌ Does NOT extract or publish lottery numbers
- ❌ Does NOT claim affiliation with any government body

---

## 📝 License

MIT License. Educational and reference purposes.
Always verify results at official government lottery websites.
