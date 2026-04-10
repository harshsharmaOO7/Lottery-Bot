/**
 * app.js — Shared JS for all lottery pages
 * ─────────────────────────────────────────
 * KEY FEATURES:
 *  • cache-bust fetch (fixes stale date bug)
 *  • Shows OLD result with banner if today's not available yet
 *  • Auto-refresh every 5 min near draw times, 10 min otherwise
 *  • Countdown timer to next draw
 */
(function () {
  'use strict';

  // ── UPDATE THESE ────────────────────────────────────────────
  var SITE_BASE = 'https://harshsharmaoo7.github.io/Lottery-Bot/';
  var RAW_BASE  = 'https://raw.githubusercontent.com/harshsharmaOO7/Lottery-Bot/main/';
  // ────────────────────────────────────────────────────────────

  var JSON_URL  = SITE_BASE + 'results.json';
  var GD_VIEW   = 'https://docs.google.com/gview?embedded=true&url=';
  var CFG       = window.PAGE_CONFIG || { draw: null, state: 'nagaland' };

  // ── IST helpers ──────────────────────────────────────────────
  function istNow() {
    var d = new Date();
    // IST = UTC + 5:30
    var utc = d.getTime() + d.getTimezoneOffset() * 60000;
    return new Date(utc + 19800000); // 5.5 * 3600 * 1000
  }
  function istDateStr() {
    var n = istNow();
    var y = n.getFullYear();
    var m = String(n.getMonth() + 1).padStart(2, '0');
    var d = String(n.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + d;
  }
  function detectDraw() {
    var h = istNow().getHours();
    if (h < 13)      return '1PM';
    else if (h < 18) return '6PM';
    else             return '8PM';
  }
  function fmtDate(s) {
    if (!s) return '';
    var p = s.split('-');
    if (p.length !== 3) return s;
    var months = ['Jan','Feb','Mar','Apr','May','Jun',
                  'Jul','Aug','Sep','Oct','Nov','Dec'];
    return parseInt(p[2]) + ' ' + months[parseInt(p[1]) - 1] + ' ' + p[0];
  }

  // ── Live clock ───────────────────────────────────────────────
  function tick() {
    var el = document.getElementById('clock');
    if (!el) return;
    var n   = istNow();
    var hh  = String(n.getHours()).padStart(2, '0');
    var mm  = String(n.getMinutes()).padStart(2, '0');
    var ss  = String(n.getSeconds()).padStart(2, '0');
    var ampm = n.getHours() < 12 ? 'AM' : 'PM';
    var h12 = n.getHours() % 12 || 12;
    el.textContent = h12 + ':' + mm + ':' + ss + ' ' + ampm + ' IST';
  }
  tick();
  setInterval(tick, 1000);
  var yrEl = document.getElementById('yr');
  if (yrEl) yrEl.textContent = new Date().getFullYear();

  // ── Dark mode ────────────────────────────────────────────────
  var root = document.documentElement;
  var dark = localStorage.getItem('theme') === 'dark' ||
    (window.matchMedia && window.matchMedia('(prefers-color-scheme:dark)').matches);
  function applyTheme() {
    root.setAttribute('data-theme', dark ? 'dark' : 'light');
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

  // ── Hamburger ────────────────────────────────────────────────
  var ham = document.getElementById('hamBtn');
  var mnav = document.getElementById('mnav');
  var mov  = document.getElementById('moverlay');
  function closeNav() {
    if (mnav) mnav.classList.remove('open');
    if (mov)  mov.classList.remove('open');
    if (ham)  { ham.classList.remove('open'); ham.setAttribute('aria-expanded','false'); }
  }
  window.closeNav = closeNav;
  if (ham && mnav) {
    ham.addEventListener('click', function () {
      var o = mnav.classList.toggle('open');
      if (mov) mov.classList.toggle('open', o);
      ham.classList.toggle('open', o);
      ham.setAttribute('aria-expanded', o ? 'true' : 'false');
    });
  }

  // ── Tabs / FAQ ───────────────────────────────────────────────
  window.showTab = function (id, btn) {
    document.querySelectorAll('.tabpanel').forEach(function (p) { p.classList.remove('on'); });
    document.querySelectorAll('.tabbt').forEach(function (b) { b.classList.remove('on'); b.setAttribute('aria-selected','false'); });
    var p = document.getElementById(id);
    if (p) p.classList.add('on');
    if (btn) { btn.classList.add('on'); btn.setAttribute('aria-selected','true'); }
  };
  window.faqToggle = function (id) {
    var el = document.getElementById(id);
    if (!el) return;
    var o = el.classList.toggle('open');
    var q = el.querySelector('.faq-q');
    if (q) q.setAttribute('aria-expanded', o ? 'true' : 'false');
  };

  // ── Today row in tables ──────────────────────────────────────
  var days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  var todayName = days[istNow().getDay()];
  document.querySelectorAll('table tbody tr').forEach(function (row) {
    var td = row.querySelector('td');
    if (td && td.textContent.trim() === todayName) row.classList.add('tod');
  });

  // ── URL builders ─────────────────────────────────────────────
  function pdfUrl(rec) {
    if (!rec) return '';
    if (rec.pdf && rec.pdf.startsWith('http'))    return rec.pdf;
    if (rec.pdf && rec.pdf.length > 3)            return RAW_BASE + rec.pdf;
    if (rec.pdf_url)                              return rec.pdf_url;
    return '';
  }
  function imgUrl(rec) {
    if (!rec) return '';
    if (rec.image && rec.image.startsWith('http')) return rec.image;
    if (rec.image && rec.image.length > 3)         return RAW_BASE + rec.image;
    return '';
  }

  // ── PDF / image callbacks ────────────────────────────────────
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
    var skel = document.getElementById('img-skel');
    if (skel) skel.style.display = 'none';
    var wrap = document.getElementById('img-wrap');
    if (wrap) {
      var ph = wrap.querySelector('.img-placeholder');
      if (!ph) {
        ph = document.createElement('div');
        ph.className = 'img-placeholder';
        ph.style.cssText = 'padding:40px;text-align:center;color:var(--muted);font-size:.85rem;';
        ph.innerHTML = '📄 Result image not yet available.<br>Please check after draw time.';
        wrap.appendChild(ph);
      }
    }
  };
  window.shareResult = function () {
    if (navigator.share) {
      navigator.share({ title: document.title, url: location.href }).catch(function(){});
    } else if (navigator.clipboard) {
      navigator.clipboard.writeText(location.href).then(function(){ alert('Link copied!'); });
    } else { prompt('Copy:', location.href); }
  };

  // ════════════════════════════════════════════════════════════
  //  STATUS BANNER — shown when displaying old result
  // ════════════════════════════════════════════════════════════
  function showOldBanner(rec, draw) {
    var existing = document.getElementById('old-result-banner');
    if (existing) existing.remove();

    var card = document.getElementById('result-card');
    if (!card) return;

    var n   = istNow();
    var h   = n.getHours();
    var min = n.getMinutes();

    // Next draw time
    var nextDraw = '', nextTime = '';
    if (h < 13)       { nextDraw = '1PM';  nextTime = '1:00 PM'; }
    else if (h < 18)  { nextDraw = '6PM';  nextTime = '6:00 PM'; }
    else if (h < 20)  { nextDraw = '8PM';  nextTime = '8:00 PM'; }
    else              { nextDraw = '1PM';  nextTime = 'Tomorrow 1:00 PM'; }

    var banner = document.createElement('div');
    banner.id = 'old-result-banner';
    banner.style.cssText = [
      'background:linear-gradient(135deg,#f59e0b,#d97706)',
      'color:#1a1a1a',
      'padding:12px 20px',
      'display:flex',
      'align-items:center',
      'justify-content:space-between',
      'flex-wrap:wrap',
      'gap:8px',
      'font-size:.82rem',
      'font-weight:600',
    ].join(';');

    banner.innerHTML =
      '<span style="display:flex;align-items:center;gap:8px;">' +
        '⏳ <span>Showing last available result — ' + fmtDate(rec.date) + ' ' + rec.draw +
        '. <strong>' + draw + '</strong> result will appear after ' + nextTime + '.</span>' +
      '</span>' +
      '<button onclick="location.reload()" style="' +
        'background:#fff;color:#1a1a1a;border:none;padding:4px 12px;' +
        'border-radius:20px;font-size:.78rem;font-weight:700;cursor:pointer;">' +
        '🔄 Refresh' +
      '</button>';

    card.insertBefore(banner, card.firstChild);
  }

  function removeBanner() {
    var b = document.getElementById('old-result-banner');
    if (b) b.remove();
  }

  // ════════════════════════════════════════════════════════════
  //  COUNTDOWN TIMER to next draw
  // ════════════════════════════════════════════════════════════
  function startCountdown() {
    var el = document.getElementById('countdown');
    if (!el) return;

    function update() {
      var n = istNow();
      var h = n.getHours(), m = n.getMinutes(), s = n.getSeconds();

      var targets = [
        { label: '1PM draw', h: 13, m: 0 },
        { label: '6PM draw', h: 18, m: 0 },
        { label: '8PM draw', h: 20, m: 0 },
      ];

      var nowSec = h * 3600 + m * 60 + s;
      var next   = null;

      for (var i = 0; i < targets.length; i++) {
        var targetSec = targets[i].h * 3600 + targets[i].m * 60;
        if (targetSec > nowSec) { next = targets[i]; next.sec = targetSec; break; }
      }

      if (!next) {
        el.textContent = 'All draws done for today';
        return;
      }

      var diff = next.sec - nowSec;
      var dh   = Math.floor(diff / 3600);
      var dm   = Math.floor((diff % 3600) / 60);
      var ds   = diff % 60;

      el.textContent = 'Next: ' + next.label + ' in ' +
        (dh > 0 ? dh + 'h ' : '') +
        String(dm).padStart(2,'0') + 'm ' +
        String(ds).padStart(2,'0') + 's';
    }
    update();
    setInterval(update, 1000);
  }
  startCountdown();

  // ════════════════════════════════════════════════════════════
  //  FIND RECORD — today first, else most recent for draw
  // ════════════════════════════════════════════════════════════
  function findRecord(data, state, draw) {
    var arr = (data[state] || []);
    if (!arr.length) return { rec: null, isToday: false };

    var today = istDateStr();

    // 1. Today + exact draw
    for (var i = 0; i < arr.length; i++) {
      if (arr[i].date === today && arr[i].draw === draw) {
        return { rec: arr[i], isToday: true };
      }
    }

    // 2. Latest with same draw (old result fallback)
    for (var j = 0; j < arr.length; j++) {
      if (arr[j].draw === draw) {
        return { rec: arr[j], isToday: false };
      }
    }

    // 3. Absolute latest (last resort)
    return { rec: arr[0], isToday: false };
  }

  // ════════════════════════════════════════════════════════════
  //  RENDER RESULT CARD
  // ════════════════════════════════════════════════════════════
  function renderResult(rec, draw, isToday) {
    if (!rec) { showError(); return; }

    // ── Banner ──
    if (!isToday) {
      showOldBanner(rec, draw);
    } else {
      removeBanner();
    }

    // ── Title + date ──
    var dname = rec.draw_name || ((rec.state || 'Nagaland') + ' Lottery ' + rec.draw);
    var titleStr = dname + ' Result — ' + fmtDate(rec.date);

    var els = {
      title:   document.getElementById('res-title'),
      date:    document.getElementById('res-date'),
      src:     document.getElementById('res-source'),
      updated: document.getElementById('last-updated'),
      ver:     document.getElementById('verified-badge'),
    };
    if (els.title)   els.title.textContent   = titleStr;
    if (els.date)    els.date.textContent     = fmtDate(rec.date) + ' · ' + rec.draw;
    if (els.src)     els.src.textContent      = (rec.source || '').replace(/^https?:\/\//,'');
    if (els.updated) els.updated.textContent  = rec.fetched_at
      ? 'Fetched: ' + rec.fetched_at.replace('T',' ').replace('+05:30',' IST')
      : 'Date: ' + rec.date;
    if (els.ver) {
      els.ver.style.display = 'inline-block';
      els.ver.textContent   = rec.verified ? '✓ Verified' : 'Unverified';
      els.ver.className     = rec.verified ? 'verified' : 'unverified';
    }

    // ── Image ──
    var iu = imgUrl(rec);
    var img = document.getElementById('res-img');
    if (img) {
      if (iu) {
        img.src   = iu;
        img.alt   = titleStr;
        img.style.display = 'none'; // onload shows it
      } else {
        var skel = document.getElementById('img-skel');
        if (skel) skel.style.display = 'none';
        var wrap = document.getElementById('img-wrap');
        if (wrap) {
          wrap.innerHTML = '<div style="padding:36px;text-align:center;color:var(--muted);font-size:.85rem;">' +
            '📄 Result image not yet available for ' + rec.draw + '.<br>Check back after draw time.' +
            '</div>';
        }
      }
    }

    // ── PDF ──
    var pu       = pdfUrl(rec);
    var dlBtn    = document.getElementById('dl-btn');
    var errBtn   = document.getElementById('pdf-err-btn');
    var pdfFrame = document.getElementById('pdf-frame');
    var pdfLoad  = document.getElementById('pdf-load');

    if (dlBtn)  dlBtn.href  = pu || rec.source || '#';
    if (errBtn) errBtn.href = pu || rec.source || '#';

    if (pu && pdfFrame) {
      pdfFrame.src = GD_VIEW + encodeURIComponent(pu);
    } else if (pdfLoad) {
      pdfLoad.style.display = 'none';
      window.pdfFail();
    }

    // ── SEO update ──
    document.title = titleStr + ' | Lottery Sambad Result';
    var md = document.querySelector('meta[name="description"]');
    if (md) md.setAttribute('content','Check ' + titleStr + '. Official PDF download. Updated automatically.');

    // ── Show card ──
    var loading = document.getElementById('loading-state');
    var card    = document.getElementById('result-card');
    if (loading) loading.style.display = 'none';
    if (card)    card.style.display    = 'block';
  }

  // ── Render history ────────────────────────────────────────────
  function renderHistory(data) {
    var grid = document.getElementById('hist-grid');
    if (!grid) return;
    var items = [];
    ['nagaland','kerala'].forEach(function(st) {
      (data[st] || []).slice(0,9).forEach(function(r){ items.push({st:st, rec:r}); });
    });
    items.sort(function(a,b){
      return (b.rec.date + b.rec.draw) > (a.rec.date + a.rec.draw) ? 1 : -1;
    });
    items = items.slice(0,10);
    if (!items.length) {
      grid.innerHTML = '<div style="grid-column:1/-1;color:var(--muted);padding:20px;text-align:center;">No history yet.</div>';
      return;
    }
    grid.innerHTML = items.map(function(it){
      var r  = it.rec;
      var pu = pdfUrl(r);
      var nm = (r.draw_name || it.st+' '+r.draw).replace(/^Dear\s/,'');
      return '<a class="hitem" href="'+(pu||'#')+'" '+(pu?'download ':'')+' >' +
        '<span>'+nm+' '+r.draw+'</span>' +
        '<span class="hitem-sub">'+fmtDate(r.date)+'</span>' +
        '<span class="hbadge">'+it.st.toUpperCase()+'</span>' +
        '</a>';
    }).join('');
  }

  // ── Render sidebar ────────────────────────────────────────────
  function renderSidebar(data) {
    var list = document.getElementById('sidebar-list');
    if (!list) return;
    var items = [];
    var dotCls = ['','b','g','r','','b'];
    var k = 0;
    (data.nagaland||[]).slice(0,4).forEach(function(r){
      items.push({ lbl:'Nagaland '+r.draw, sub:fmtDate(r.date), dc:dotCls[k++%6] });
    });
    (data.kerala||[]).slice(0,2).forEach(function(r){
      items.push({ lbl:'Kerala '+(r.draw_name||r.draw||'3PM'), sub:fmtDate(r.date), dc:dotCls[k++%6] });
    });
    list.innerHTML = items.map(function(it){
      return '<li><a class="sri" href="#">' +
        '<span class="dot '+it.dc+'" aria-hidden="true"></span>' +
        '<span class="si"><span class="sn">'+it.lbl+'</span><span class="st">'+it.sub+'</span></span>' +
        '<span class="sa">›</span></a></li>';
    }).join('');
  }

  // ── Error state ───────────────────────────────────────────────
  function showError() {
    document.getElementById('loading-state') && (document.getElementById('loading-state').style.display='none');
    document.getElementById('result-card')   && (document.getElementById('result-card').style.display='none');
    var e = document.getElementById('error-state');
    if (e) e.style.display = 'block';
  }

  // ════════════════════════════════════════════════════════════
  //  MAIN FETCH
  // ════════════════════════════════════════════════════════════
  var lastFetchedAt = null;

  function loadData() {
    // Cache-bust — prevents browser from serving stale JSON
    var bust = '?v=' + Date.now();
    var ctrl = new AbortController();
    var to   = setTimeout(function(){ ctrl.abort(); }, 10000);

    fetch(JSON_URL + bust, { signal: ctrl.signal })
      .then(function(r) {
        clearTimeout(to);
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function(data) {
        lastFetchedAt = new Date();

        var draw  = CFG.draw || detectDraw();
        var state = CFG.state || 'nagaland';

        var found = findRecord(data, state, draw);
        renderResult(found.rec, draw, found.isToday);
        renderHistory(data);
        renderSidebar(data);
      })
      .catch(function(err) {
        clearTimeout(to);
        console.warn('Fetch failed:', err.message);

        // Try to use last known data from cache or show error
        if (!lastFetchedAt) {
          showError();
        }
        // If we had data before, silently keep showing it
      });
  }

  // ── Auto-refresh logic ────────────────────────────────────────
  function scheduleRefresh() {
    var h = istNow().getHours();
    var m = istNow().getMinutes();

    // Near draw times — refresh every 3 min
    var nearDraw =
      (h === 12 && m >= 55) || (h === 13 && m < 15) ||
      (h === 17 && m >= 55) || (h === 18 && m < 15) ||
      (h === 19 && m >= 55) || (h === 20 && m < 15);

    var interval = nearDraw ? 3 * 60 * 1000 : 10 * 60 * 1000;
    setTimeout(function() {
      loadData();
      scheduleRefresh(); // reschedule dynamically
    }, interval);
  }

  // ── INIT ──────────────────────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      loadData();
      scheduleRefresh();
    });
  } else {
    loadData();
    scheduleRefresh();
  }

})();
