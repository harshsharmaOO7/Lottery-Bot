/**
 * app.js — Lottery Sambad Result Frontend
 * =========================================
 * Handles: IST clock, draw detection, JSON fetch, result render,
 *          history grid, sidebar, dark mode, FAQ, share, countdown.
 *
 * Image URL logic:
 *   - If image starts with "https://" → use directly (live scrape URL)
 *   - If image starts with "images/"  → prefix with RAW_BASE (locally stored)
 *   - If image is empty               → show "not available" placeholder
 */
(function () {
'use strict';

var SITE_BASE = 'https://harshsharmaoo7.github.io/Lottery-Bot/';
var RAW_BASE  = 'https://raw.githubusercontent.com/harshsharmaOO7/Lottery-Bot/main/';
var JSON_URL  = SITE_BASE + 'results.json';
var CFG       = window.PAGE_CONFIG || { draw: null, state: 'nagaland' };

// ── IST helpers ────────────────────────────────────────────────────
function istNow() {
  return new Date(Date.now() + (5 * 60 + 30) * 60 * 1000 + new Date().getTimezoneOffset() * 60 * 1000);
}
function istDateStr() {
  var n = istNow();
  return n.getFullYear() + '-' +
    String(n.getMonth() + 1).padStart(2, '0') + '-' +
    String(n.getDate()).padStart(2, '0');
}
function detectDraw() {
  var h = istNow().getHours();
  return h < 13 ? '1PM' : h < 18 ? '6PM' : '8PM';
}
function fmtDate(s) {
  if (!s) return '';
  var p = s.split('-');
  if (p.length !== 3) return s;
  var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return parseInt(p[2]) + ' ' + months[parseInt(p[1]) - 1] + ' ' + p[0];
}

// ── Live IST Clock ─────────────────────────────────────────────────
function updateClock() {
  var el = document.getElementById('clock');
  if (!el) return;
  var n    = istNow();
  var h    = n.getHours();
  var mi   = n.getMinutes();
  var s    = n.getSeconds();
  var ampm = h >= 12 ? 'PM' : 'AM';
  var h12  = h % 12 || 12;
  el.textContent =
    String(h12).padStart(2, '0') + ':' +
    String(mi).padStart(2, '0') + ':' +
    String(s).padStart(2, '0') + ' ' + ampm + ' IST';
}
updateClock();
setInterval(updateClock, 1000);

// Footer year
var yrEl = document.getElementById('yr');
if (yrEl) yrEl.textContent = new Date().getFullYear();

// ── Highlight current draw tab ─────────────────────────────────────
(function () {
  var draw = CFG.draw || detectDraw();
  var map = { '1PM': 'tab-1pm', '6PM': 'tab-6pm', '8PM': 'tab-8pm' };
  var id  = map[draw];
  if (id) { var el = document.getElementById(id); if (el) el.classList.add('on'); }
})();

// ── Dark mode ──────────────────────────────────────────────────────
var dark = localStorage.getItem('theme') === 'dark' ||
  (window.matchMedia && window.matchMedia('(prefers-color-scheme:dark)').matches);
function applyTheme() {
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
  var b = document.getElementById('themeBtn');
  if (b) b.textContent = dark ? '☀️' : '🌙';
}
applyTheme();
var tb = document.getElementById('themeBtn');
if (tb) tb.addEventListener('click', function () {
  dark = !dark;
  localStorage.setItem('theme', dark ? 'dark' : 'light');
  applyTheme();
});

// ── Hamburger ──────────────────────────────────────────────────────
var ham  = document.getElementById('hamBtn');
var mnav = document.getElementById('mnav');
var mov  = document.getElementById('moverlay');
window.closeNav = function () {
  if (mnav) mnav.classList.remove('open');
  if (mov)  mov.classList.remove('open');
  if (ham)  { ham.classList.remove('open'); ham.setAttribute('aria-expanded', 'false'); }
};
if (ham && mnav) {
  ham.addEventListener('click', function () {
    var o = mnav.classList.toggle('open');
    if (mov) mov.classList.toggle('open', o);
    ham.classList.toggle('open', o);
    ham.setAttribute('aria-expanded', o ? 'true' : 'false');
  });
}

// ── FAQ ────────────────────────────────────────────────────────────
window.faqToggle = function (id) {
  var el = document.getElementById(id);
  if (el) el.classList.toggle('open');
};

// ── Today row highlight in schedule tables ─────────────────────────
var DAYS = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
document.querySelectorAll('table tbody tr').forEach(function (row) {
  var td = row.querySelector('td');
  if (td && td.textContent.trim() === DAYS[istNow().getDay()])
    row.classList.add('tod');
});

// ── Share ──────────────────────────────────────────────────────────
window.shareResult = function () {
  if (navigator.share)
    navigator.share({ title: document.title, url: location.href }).catch(function(){});
  else if (navigator.clipboard)
    navigator.clipboard.writeText(location.href).then(function(){ alert('Link copied!'); });
  else
    prompt('Copy this link:', location.href);
};

// ── Image handlers ─────────────────────────────────────────────────
window.onImgLoad = function (img) {
  img.style.display = 'block';
  var sk = document.getElementById('img-skel');
  if (sk) sk.style.display = 'none';
};
window.onImgFail = function (img) {
  img.style.display = 'none';
  var sk = document.getElementById('img-skel');
  if (sk) sk.style.display = 'none';
  var wrap = document.getElementById('img-wrap');
  if (wrap && !wrap.querySelector('.img-err')) {
    var d = document.createElement('div');
    d.className = 'img-err';
    d.style.cssText = 'padding:40px;text-align:center;color:var(--muted);font-size:.85rem;';
    d.innerHTML = '📸 Image abhi available nahi hai<br><small>Result publish hone ke baad dikhegi</small>';
    wrap.appendChild(d);
  }
};

// ── Image URL resolver ─────────────────────────────────────────────
// Priority:
//   1. Full https:// URL (live scrape from lotterysambadresult.in) → use directly
//   2. Relative "images/..." path → prefix RAW_BASE
//   3. Empty → return ""
function imgURL(rec) {
  var img = (rec && rec.image) || '';
  if (!img) return '';
  if (img.startsWith('http')) return img;       // External URL — use directly
  return RAW_BASE + img;                         // Local file — serve via raw GitHub
}

// ── Old-result banner ──────────────────────────────────────────────
function showBanner(rec, draw) {
  var old = document.getElementById('old-banner');
  if (old) old.remove();
  var card = document.getElementById('result-card');
  if (!card) return;
  var h = istNow().getHours();
  var nextTime = h < 13 ? '1:00 PM' : h < 18 ? '6:00 PM' : h < 20 ? '8:00 PM' : 'kal 1:00 PM';
  var b = document.createElement('div');
  b.id = 'old-banner';
  b.style.cssText = [
    'background:linear-gradient(135deg,#f59e0b,#d97706)',
    'color:#1a1a1a','padding:12px 16px',
    'display:flex','align-items:flex-start','justify-content:space-between',
    'gap:10px','flex-wrap:wrap','font-size:.82rem','font-weight:600'
  ].join(';');
  b.innerHTML =
    '<div style="display:flex;gap:8px;flex:1;align-items:flex-start;">' +
      '<span style="font-size:1.1rem;flex-shrink:0;">⏳</span>' +
      '<span>' +
        '<strong>' + draw + ' ka naya result abhi nahi aaya.</strong><br>' +
        'Last result: <strong>' + fmtDate(rec.date) + ' · ' + rec.draw + '</strong><br>' +
        'Naya result <strong>' + nextTime + '</strong> ke baad update hoga.' +
      '</span>' +
    '</div>' +
    '<button onclick="location.reload()" style="background:#fff;color:#1a1a1a;border:none;' +
      'padding:5px 14px;border-radius:20px;font-size:.78rem;font-weight:700;cursor:pointer;flex-shrink:0;">' +
      '🔄 Refresh' +
    '</button>';
  card.insertBefore(b, card.firstChild);
}

// ── Countdown to next draw ─────────────────────────────────────────
function startCountdown() {
  var el = document.getElementById('countdown');
  if (!el) return;
  function update() {
    var n   = istNow();
    var sec = n.getHours() * 3600 + n.getMinutes() * 60 + n.getSeconds();
    var targets = [
      { l: '1PM draw', s: 13 * 3600 },
      { l: '6PM draw', s: 18 * 3600 },
      { l: '8PM draw', s: 20 * 3600 },
    ];
    var next = null;
    for (var i = 0; i < targets.length; i++) {
      if (targets[i].s > sec) { next = targets[i]; break; }
    }
    if (!next) { el.textContent = 'Aaj ke sabhi draws ho gaye ✓'; return; }
    var diff = next.s - sec;
    var hh = Math.floor(diff / 3600);
    var mm = Math.floor((diff % 3600) / 60);
    var ss = diff % 60;
    el.textContent = 'Next: ' + next.l + ' in ' +
      (hh > 0 ? hh + 'h ' : '') +
      String(mm).padStart(2, '0') + 'm ' +
      String(ss).padStart(2, '0') + 's';
  }
  update();
  setInterval(update, 1000);
}
startCountdown();

// ── Find best matching record ──────────────────────────────────────
function findRecord(data, state, draw) {
  var arr   = data[state] || [];
  var today = istDateStr();
  // 1. Today + exact draw
  for (var i = 0; i < arr.length; i++)
    if (arr[i].date === today && arr[i].draw === draw)
      return { rec: arr[i], isToday: true };
  // 2. Latest record for this draw (any date)
  for (var j = 0; j < arr.length; j++)
    if (arr[j].draw === draw)
      return { rec: arr[j], isToday: false };
  // 3. Absolute latest
  if (arr.length) return { rec: arr[0], isToday: false };
  return { rec: null, isToday: false };
}

// ── Render result card ─────────────────────────────────────────────
function renderResult(rec, draw, isToday) {
  if (!rec) { showError(); return; }

  if (!isToday) showBanner(rec, draw);
  else { var ob = document.getElementById('old-banner'); if (ob) ob.remove(); }

  var dname    = rec.draw_name || ('Nagaland ' + rec.draw);
  var titleStr = dname + ' Result — ' + fmtDate(rec.date);
  var E = function (id) { return document.getElementById(id); };

  if (E('res-title'))    E('res-title').textContent   = titleStr;
  if (E('res-date'))     E('res-date').textContent     = fmtDate(rec.date) + ' · ' + rec.draw;
  if (E('res-source'))   E('res-source').textContent   = (rec.source || '').replace(/^https?:\/\//, '');
  if (E('last-updated')) E('last-updated').textContent =
    rec.fetched_at
      ? '🕐 Updated: ' + rec.fetched_at.replace('T', ' ').replace('+05:30', ' IST').replace('+00:00', ' UTC')
      : '📅 ' + rec.date;

  var vb = E('verified-badge');
  if (vb) {
    vb.style.display = 'inline-block';
    vb.textContent   = rec.verified ? '✓ Verified' : 'Unverified';
    vb.className     = rec.verified ? 'verified' : 'unverified';
  }

  // Image
  var iu    = imgURL(rec);
  var imgEl = E('res-img');
  var skEl  = E('img-skel');
  if (imgEl) {
    if (iu) {
      imgEl.src = iu;
      imgEl.alt = titleStr;
      imgEl.style.display = 'none';
    } else {
      if (skEl) skEl.style.display = 'none';
      var wrap = E('img-wrap');
      if (wrap) wrap.innerHTML =
        '<div style="padding:48px 20px;text-align:center;color:var(--muted);">' +
        '<div style="font-size:2.5rem;margin-bottom:12px;">📸</div>' +
        '<p style="font-weight:600;">Result image abhi available nahi hai</p>' +
        '<p style="font-size:.8rem;margin-top:6px;opacity:.7;">Draw ke baad yahan dikhegi</p>' +
        '</div>';
    }
  }

  // Download button
  var dl = E('dl-btn');
  if (dl) {
    if (iu) {
      dl.href = iu;
      dl.setAttribute('download', 'lottery-' + rec.date + '-' + draw + '.jpg');
      dl.style.display = 'inline-flex';
    } else {
      dl.style.display = 'none';
    }
  }

  // SEO title
  document.title = titleStr + ' | Lottery Sambad Result Today';

  if (E('loading-state')) E('loading-state').style.display = 'none';
  if (E('error-state'))   E('error-state').style.display   = 'none';
  if (E('result-card'))   E('result-card').style.display   = 'block';
}

// ── Render history grid ────────────────────────────────────────────
function renderHistory(data, filterDraw) {
  var grid = document.getElementById('hist-grid');
  if (!grid) return;

  var items = [];
  var nagaland = data['nagaland'] || [];

  // Filter by draw if on a draw-specific page
  var source = filterDraw
    ? nagaland.filter(function(r){ return r.draw === filterDraw; })
    : nagaland;

  source.slice(0, 12).forEach(function(r) {
    items.push({ st: 'nagaland', rec: r });
  });

  // Also add kerala on homepage
  if (!filterDraw) {
    (data['kerala'] || []).slice(0, 4).forEach(function(r){
      items.push({ st: 'kerala', rec: r });
    });
    items.sort(function(a, b){
      return (b.rec.date + b.rec.draw) > (a.rec.date + a.rec.draw) ? 1 : -1;
    });
    items = items.slice(0, 12);
  }

  if (!items.length) {
    grid.innerHTML = '<div style="grid-column:1/-1;padding:20px;text-align:center;color:var(--muted);">No history yet.</div>';
    return;
  }

  grid.innerHTML = items.map(function(it) {
    var r   = it.rec;
    var iu  = imgURL(r);
    var nm  = (r.draw_name || it.st + ' ' + r.draw).replace(/^Dear\s/, '');
    var hasImg = iu ? 'href="' + iu + '" target="_blank" rel="noopener"' : 'href="#"';
    return '<a class="hitem" ' + hasImg + '>' +
      '<span>' + nm + ' <strong>' + r.draw + '</strong></span>' +
      '<span class="hitem-sub">' + fmtDate(r.date) + '</span>' +
      '<span class="hbadge">' + (r.seeded ? 'PDF' : it.st.toUpperCase()) + '</span>' +
      '</a>';
  }).join('');
}

// ── Render sidebar ─────────────────────────────────────────────────
function renderSidebar(data) {
  var list = document.getElementById('sidebar-list');
  if (!list) return;
  var dc = ['', 'b', 'g', 'r', '', 'b'];
  var k = 0, items = [];
  (data.nagaland || []).slice(0, 5).forEach(function(r) {
    items.push({ lbl: 'Nagaland ' + r.draw, sub: fmtDate(r.date), d: dc[k++ % 6] });
  });
  (data.kerala || []).slice(0, 2).forEach(function(r) {
    items.push({ lbl: 'Kerala ' + (r.draw_name || r.draw || '3PM'), sub: fmtDate(r.date), d: dc[k++ % 6] });
  });
  list.innerHTML = items.map(function(it) {
    return '<li><div class="sri">' +
      '<span class="dot ' + it.d + '"></span>' +
      '<span class="si"><span class="sn">' + it.lbl + '</span>' +
      '<span class="st">' + it.sub + '</span></span>' +
      '<span class="sa">›</span></div></li>';
  }).join('');
}

// ── Error state ────────────────────────────────────────────────────
function showError() {
  var E = function(id){ return document.getElementById(id); };
  if (E('loading-state')) E('loading-state').style.display = 'none';
  if (E('result-card'))   E('result-card').style.display   = 'none';
  if (E('error-state'))   E('error-state').style.display   = 'block';
}

// ── Fetch JSON + render ────────────────────────────────────────────
function loadData() {
  var url  = JSON_URL + '?t=' + Date.now();
  var ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null;
  var to   = ctrl ? setTimeout(function(){ ctrl.abort(); }, 10000) : null;

  var opts = { cache: 'no-store' };
  if (ctrl) opts.signal = ctrl.signal;

  fetch(url, opts)
    .then(function(r) {
      if (to) clearTimeout(to);
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(function(data) {
      var draw      = CFG.draw  || detectDraw();
      var state     = CFG.state || 'nagaland';
      var found     = findRecord(data, state, draw);
      renderResult(found.rec, draw, found.isToday);
      renderHistory(data, CFG.draw);   // filter by draw on draw-specific pages
      renderSidebar(data);
    })
    .catch(function(err) {
      if (to) clearTimeout(to);
      console.warn('Fetch error:', err.message);
      var card = document.getElementById('result-card');
      if (card && card.style.display === 'none') showError();
    });
}

// ── Auto refresh (smart — near draw times: 3 min, else: 10 min) ───
function scheduleRefresh() {
  var h = istNow().getHours();
  var m = istNow().getMinutes();
  var near = (h === 12 && m >= 50) || (h === 13 && m <= 20) ||
             (h === 17 && m >= 50) || (h === 18 && m <= 20) ||
             (h === 19 && m >= 50) || (h === 20 && m <= 20);
  setTimeout(function(){ loadData(); scheduleRefresh(); }, near ? 3*60*1000 : 10*60*1000);
}

// ── Init ───────────────────────────────────────────────────────────
if (document.readyState === 'loading')
  document.addEventListener('DOMContentLoaded', function(){ loadData(); scheduleRefresh(); });
else { loadData(); scheduleRefresh(); }

})();
