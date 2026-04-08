/**
 * app.js — Shared JavaScript for all lottery result pages
 * ─────────────────────────────────────────────────────────
 * • Fetches results.json with cache-bust (fixes stale date bug)
 * • Renders result card, PDF viewer, history
 * • Dark mode, hamburger, FAQ accordion, tab switcher
 * • Auto-refresh every 10 minutes
 *
 * Each page sets window.PAGE_CONFIG before loading this script:
 *   window.PAGE_CONFIG = { draw: "8PM", state: "nagaland" }
 */

(function () {
  'use strict';

  /* ─── CONFIG (defaults, overridden by each page) ──────── */
  var CFG = window.PAGE_CONFIG || { draw: null, state: 'nagaland' };

  /* ── CHANGE THIS to your GitHub raw base URL ─────────── */
  var RAW_BASE = 'https://raw.githubusercontent.com/harshsharmaOO7/Lottery-Bot/main/';
  /* ── CHANGE THIS to your GitHub Pages base URL ───────── */
  var SITE_BASE = 'https://harshsharmaoo7.github.io/Lottery-Bot/';
  var JSON_URL  = SITE_BASE + 'results.json';
  var GD_VIEWER = 'https://docs.google.com/gview?embedded=true&url=';

  /* ─── LIVE IST CLOCK ──────────────────────────────────── */
  function tick() {
    var el = document.getElementById('clock');
    if (!el) return;
    el.textContent = new Date().toLocaleTimeString('en-IN', {
      timeZone: 'Asia/Kolkata', hour: '2-digit',
      minute: '2-digit', second: '2-digit', hour12: true
    }) + ' IST';
  }
  tick();
  setInterval(tick, 1000);

  /* ─── FOOTER YEAR ─────────────────────────────────────── */
  var yrEl = document.getElementById('yr');
  if (yrEl) yrEl.textContent = new Date().getFullYear();

  /* ─── DETECT DRAW FROM IST TIME ───────────────────────── */
  function detectDraw() {
    var h = new Date().toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata', hour: 'numeric', hour12: false
    });
    h = parseInt(h, 10);
    if (h < 14)      return '1PM';
    else if (h < 19) return '6PM';
    else             return '8PM';
  }

  /* ─── DARK MODE ───────────────────────────────────────── */
  var root = document.documentElement;
  var dark = localStorage.getItem('theme') === 'dark' ||
    (window.matchMedia && window.matchMedia('(prefers-color-scheme:dark)').matches);

  function applyTheme() {
    root.setAttribute('data-theme', dark ? 'dark' : 'light');
    var btn = document.getElementById('themeBtn');
    if (btn) btn.textContent = dark ? '☀️' : '🌙';
  }
  applyTheme();

  var thBtn = document.getElementById('themeBtn');
  if (thBtn) {
    thBtn.addEventListener('click', function () {
      dark = !dark;
      localStorage.setItem('theme', dark ? 'dark' : 'light');
      applyTheme();
    });
  }

  /* ─── HAMBURGER ───────────────────────────────────────── */
  var hamBtn  = document.getElementById('hamBtn');
  var mnavEl  = document.getElementById('mnav');
  var overlayEl = document.getElementById('moverlay');

  function closeNav() {
    if (mnavEl)    mnavEl.classList.remove('open');
    if (overlayEl) overlayEl.classList.remove('open');
    if (hamBtn)  { hamBtn.classList.remove('open'); hamBtn.setAttribute('aria-expanded', 'false'); }
  }
  window.closeNav = closeNav;

  if (hamBtn && mnavEl) {
    hamBtn.addEventListener('click', function () {
      var open = mnavEl.classList.toggle('open');
      if (overlayEl) overlayEl.classList.toggle('open', open);
      hamBtn.classList.toggle('open', open);
      hamBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }
  document.addEventListener('click', function (e) {
    if (mnavEl && mnavEl.classList.contains('open') &&
        !mnavEl.contains(e.target) && hamBtn && !hamBtn.contains(e.target)) {
      closeNav();
    }
  });

  /* ─── SCHEDULE TABS ───────────────────────────────────── */
  window.showTab = function (id, btn) {
    document.querySelectorAll('.tabpanel').forEach(function (p) { p.classList.remove('on'); });
    document.querySelectorAll('.tabbt').forEach(function (b) {
      b.classList.remove('on'); b.setAttribute('aria-selected', 'false');
    });
    var p = document.getElementById(id);
    if (p) p.classList.add('on');
    if (btn) { btn.classList.add('on'); btn.setAttribute('aria-selected', 'true'); }
  };

  /* ─── FAQ ─────────────────────────────────────────────── */
  window.faqToggle = function (id) {
    var item = document.getElementById(id);
    if (!item) return;
    var open = item.classList.toggle('open');
    var q = item.querySelector('.faq-q');
    if (q) q.setAttribute('aria-expanded', open ? 'true' : 'false');
  };

  /* ─── TODAY ROW IN TABLES ─────────────────────────────── */
  var days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  var todayName = days[new Date().getDay()];
  document.querySelectorAll('table tbody tr').forEach(function (row) {
    var td = row.querySelector('td');
    if (td && td.textContent.trim() === todayName) row.classList.add('tod');
  });

  /* ─── URL BUILDERS ────────────────────────────────────── */
  function pdfUrl(rec) {
    if (!rec) return '';
    // Use absolute URL first, then construct from RAW_BASE
    if (rec.pdf && rec.pdf.startsWith('http')) return rec.pdf;
    if (rec.pdf)     return RAW_BASE + rec.pdf;
    if (rec.pdf_url) return rec.pdf_url;
    return '';
  }

  function imgUrl(rec) {
    if (!rec) return '';
    if (rec.image && rec.image.startsWith('http')) return rec.image;
    if (rec.image)   return RAW_BASE + rec.image;
    return '';
  }

  /* ─── DATE FORMATTER ──────────────────────────────────── */
  function fmtDate(d) {
    if (!d) return 'Date unavailable';
    // Parse YYYY-MM-DD in IST (avoid UTC shift)
    var parts = d.split('-');
    if (parts.length === 3) {
      var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      return parseInt(parts[2], 10) + ' ' + months[parseInt(parts[1], 10) - 1] + ' ' + parts[0];
    }
    return d;
  }

  /* ─── PDF CALLBACKS ───────────────────────────────────── */
  window.pdfLoaded = function () {
    var l = document.getElementById('pdf-load');
    var f = document.getElementById('pdf-frame');
    if (l) l.style.display = 'none';
    if (f) f.style.display = 'block';
  };
  window.pdfFail = function () {
    var l = document.getElementById('pdf-load');
    var f = document.getElementById('pdf-frame');
    var e = document.getElementById('pdf-err');
    if (l) l.style.display = 'none';
    if (f) f.style.display = 'none';
    if (e) e.style.display = 'block';
  };
  window.imgFail = function (img) {
    img.style.display = 'none';
    var prev = img.previousElementSibling;
    if (prev && prev.classList.contains('skel')) {
      prev.style.display = 'none';
      var wrap = img.parentElement;
      if (wrap) {
        var ph = document.createElement('div');
        ph.className = 'err-box';
        ph.innerHTML = '<p>Result image not yet available.<br>Please check after draw time.</p>';
        wrap.appendChild(ph);
      }
    }
  };

  /* ─── SHARE ───────────────────────────────────────────── */
  window.shareResult = function () {
    if (navigator.share) {
      navigator.share({ title: document.title, url: location.href }).catch(function(){});
    } else if (navigator.clipboard) {
      navigator.clipboard.writeText(location.href).then(function () {
        alert('Link copied!');
      });
    } else {
      prompt('Copy this link:', location.href);
    }
  };

  /* ─── FIND RECORD ─────────────────────────────────────── */
  function findRecord(data, state, draw) {
    var arr = data[state] || [];
    if (!arr.length) return null;

    // TODAY's IST date string
    var istNow = new Date().toLocaleString('en-CA', {
      timeZone: 'Asia/Kolkata', year: 'numeric',
      month: '2-digit', day: '2-digit'
    }); // returns YYYY-MM-DD

    // 1st: today + requested draw
    for (var i = 0; i < arr.length; i++) {
      if (arr[i].draw === draw && arr[i].date === istNow) return arr[i];
    }
    // 2nd: latest with requested draw (any date)
    if (draw) {
      for (var j = 0; j < arr.length; j++) {
        if (arr[j].draw === draw) return arr[j];
      }
    }
    // 3rd: absolute latest
    return arr[0];
  }

  /* ─── RENDER MAIN RESULT ──────────────────────────────── */
  function renderResult(rec, draw) {
    if (!rec) { showErr(); return; }

    /* ── title + date ── */
    var dname = rec.draw_name || (rec.state || 'Nagaland') + ' Lottery ' + rec.draw;
    var titleStr = dname + ' Result — ' + fmtDate(rec.date);

    var titleEl = document.getElementById('res-title');
    var dateEl  = document.getElementById('res-date');
    var srcEl   = document.getElementById('res-source');
    var updEl   = document.getElementById('last-updated');
    var verEl   = document.getElementById('verified-badge');

    if (titleEl) titleEl.textContent = titleStr;
    if (dateEl)  dateEl.textContent  = fmtDate(rec.date) + ' · ' + rec.draw;
    if (srcEl)   srcEl.textContent   = (rec.source || 'official source').replace(/^https?:\/\//,'');
    if (updEl)   updEl.textContent   = 'Fetched: ' + (rec.fetched_at || rec.date);
    if (verEl) {
      verEl.style.display = 'inline-block';
      verEl.textContent   = rec.verified ? '✓ Verified' : 'Unverified';
      verEl.className     = rec.verified ? 'verified' : 'unverified';
    }

    /* ── image ── */
    var iu = imgUrl(rec);
    var img = document.getElementById('res-img');
    var skel = document.getElementById('img-skel');
    if (img) {
      if (iu) {
        img.src = iu;
        img.alt = titleStr;
        img.style.display = 'none'; // show on onload
      } else {
        if (skel) skel.style.display = 'none';
        var wrap = document.getElementById('img-wrap');
        if (wrap) {
          wrap.innerHTML = '<div class="err-box"><p>Result image not yet available</p></div>';
        }
      }
    }

    /* ── PDF ── */
    var pu = pdfUrl(rec);
    var dlBtn      = document.getElementById('dl-btn');
    var pdfErrBtn  = document.getElementById('pdf-err-btn');
    var pdfFrame   = document.getElementById('pdf-frame');
    var pdfLoad    = document.getElementById('pdf-load');

    if (dlBtn)     dlBtn.href = pu || '#';
    if (pdfErrBtn) pdfErrBtn.href = pu || rec.source || '#';

    if (pu && pdfFrame) {
      pdfFrame.src = GD_VIEWER + encodeURIComponent(pu);
    } else {
      if (pdfLoad) pdfLoad.style.display = 'none';
      window.pdfFail();
    }

    /* ── page SEO (live update) ── */
    document.title = titleStr + ' | Lottery Sambad Result';
    var metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc) {
      metaDesc.setAttribute('content',
        'Check ' + titleStr + '. Official PDF download. Updated automatically.');
    }

    /* ── show card ── */
    var card = document.getElementById('result-card');
    var loading = document.getElementById('loading-state');
    if (loading) loading.style.display = 'none';
    if (card)    card.style.display = 'block';
  }

  /* ─── RENDER HISTORY ──────────────────────────────────── */
  function renderHistory(data) {
    var grid = document.getElementById('hist-grid');
    if (!grid) return;

    var items = [];
    var states = ['nagaland', 'kerala'];
    states.forEach(function (st) {
      (data[st] || []).slice(0, 9).forEach(function (r) {
        items.push({ state: st, rec: r });
      });
    });
    // Sort newest first
    items.sort(function (a, b) {
      return (b.rec.date + b.rec.draw) > (a.rec.date + a.rec.draw) ? 1 : -1;
    });
    items = items.slice(0, 10);

    if (!items.length) {
      grid.innerHTML = '<div class="err-box" style="grid-column:1/-1"><p>No history yet</p></div>';
      return;
    }

    grid.innerHTML = items.map(function (it) {
      var r  = it.rec;
      var pu = pdfUrl(r);
      var label = (r.draw_name || (it.state + ' ' + r.draw)).replace('Dear','').trim();
      return '<a class="hitem" href="' + (pu || '#') + '" ' +
        (pu ? 'download ' : 'target="_blank" ') + '>' +
        '<span>' + label + ' ' + r.draw + '</span>' +
        '<span class="hitem-sub">' + fmtDate(r.date) + '</span>' +
        '<span class="hbadge">' + it.state.toUpperCase() + '</span>' +
        '</a>';
    }).join('');
  }

  /* ─── RENDER SIDEBAR ──────────────────────────────────── */
  function renderSidebar(data) {
    var list = document.getElementById('sidebar-list');
    if (!list) return;
    var items = [];
    var dotCls = ['', 'b', 'g', 'r', '', 'b'];
    var k = 0;
    (data.nagaland || []).slice(0, 4).forEach(function (r) {
      items.push({ lbl: 'Nagaland ' + r.draw, sub: fmtDate(r.date), dc: dotCls[k++ % 6] });
    });
    (data.kerala || []).slice(0, 2).forEach(function (r) {
      items.push({ lbl: 'Kerala ' + (r.draw_name || r.draw || '3PM'), sub: fmtDate(r.date), dc: dotCls[k++ % 6] });
    });
    list.innerHTML = items.map(function (it) {
      return '<li><a class="sri" href="#">' +
        '<span class="dot ' + it.dc + '" aria-hidden="true"></span>' +
        '<span class="si"><span class="sn">' + it.lbl + '</span>' +
        '<span class="st">' + it.sub + '</span></span>' +
        '<span class="sa">›</span></a></li>';
    }).join('');
  }

  /* ─── ERROR STATE ─────────────────────────────────────── */
  function showErr() {
    var loading = document.getElementById('loading-state');
    var card    = document.getElementById('result-card');
    var errBox  = document.getElementById('error-state');
    if (loading) loading.style.display = 'none';
    if (card)    card.style.display = 'none';
    if (errBox)  errBox.style.display = 'block';
  }

  /* ─── MAIN FETCH ──────────────────────────────────────── */
  function loadData() {
    // Cache-bust with timestamp (fixes stale date bug!)
    var bust = '?v=' + Date.now();
    var ctrl = new AbortController();
    var to   = setTimeout(function () { ctrl.abort(); }, 10000);

    fetch(JSON_URL + bust, { signal: ctrl.signal })
      .then(function (r) {
        clearTimeout(to);
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        // Determine draw: use PAGE_CONFIG, else auto-detect
        var draw = CFG.draw || detectDraw();
        var state = CFG.state || 'nagaland';

        var rec = findRecord(data, state, draw);
        renderResult(rec, draw);
        renderHistory(data);
        renderSidebar(data);
      })
      .catch(function (err) {
        console.warn('JSON fetch failed:', err.message);
        showErr();
      });
  }

  /* ─── INIT ────────────────────────────────────────────── */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadData);
  } else {
    loadData();
  }

  // Auto-refresh every 10 minutes
  setInterval(loadData, 10 * 60 * 1000);

})();
