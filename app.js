/**
 * app.js — Lottery Result Frontend (Image-Only System)
 * ─────────────────────────────────────────────────────
 * Changes from old version:
 *  • PDF section completely removed
 *  • Image loads directly from source URL (no RAW_BASE needed)
 *  • Old result banner when today's result not yet available
 *  • Cache-bust on every fetch (fixes stale date bug)
 *  • Countdown timer to next draw
 *  • Auto-refresh every 5 min near draw times
 */
(function () {
  'use strict';

  // ── UPDATE THIS ────────────────────────────────────────────
  var SITE_BASE = 'https://harshsharmaoo7.github.io/Lottery-Bot/';
  // ──────────────────────────────────────────────────────────

  var JSON_URL = SITE_BASE + 'results.json';
  var CFG      = window.PAGE_CONFIG || { draw: null, state: 'nagaland' };

  // ── IST helpers ──────────────────────────────────────────────
  function istNow() {
    return new Date(new Date().getTime() + (5.5 * 3600 * 1000) + new Date().getTimezoneOffset() * 60000);
  }
  function istDateStr() {
    var n = istNow();
    return n.getFullYear() + '-' +
      String(n.getMonth()+1).padStart(2,'0') + '-' +
      String(n.getDate()).padStart(2,'0');
  }
  function fmtDate(s) {
    if (!s) return '';
    var p = s.split('-');
    if (p.length !== 3) return s;
    var m = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return parseInt(p[2]) + ' ' + m[parseInt(p[1])-1] + ' ' + p[0];
  }
  function detectDraw() {
    var h = istNow().getHours();
    if (h < 13)      return '1PM';
    else if (h < 18) return '6PM';
    else             return '8PM';
  }

  // ── Live IST clock ───────────────────────────────────────────
  function tick() {
    var el = document.getElementById('clock');
    if (!el) return;
    var n = istNow();
    var h = n.getHours(), mi = n.getMinutes(), s = n.getSeconds();
    var ampm = h < 12 ? 'AM' : 'PM';
    var h12  = h % 12 || 12;
    el.textContent = h12 + ':' + String(mi).padStart(2,'0') + ':' +
      String(s).padStart(2,'0') + ' ' + ampm + ' IST';
  }
  tick();
  setInterval(tick, 1000);
  var yr = document.getElementById('yr');
  if (yr) yr.textContent = new Date().getFullYear();

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
  if (tb) tb.addEventListener('click', function(){
    dark = !dark;
    localStorage.setItem('theme', dark ? 'dark' : 'light');
    applyTheme();
  });

  // ── Hamburger ─────────────────────────────────────────────────
  var ham  = document.getElementById('hamBtn');
  var mnav = document.getElementById('mnav');
  var mov  = document.getElementById('moverlay');
  function closeNav(){
    if(mnav) mnav.classList.remove('open');
    if(mov)  mov.classList.remove('open');
    if(ham){ ham.classList.remove('open'); ham.setAttribute('aria-expanded','false'); }
  }
  window.closeNav = closeNav;
  if(ham && mnav){
    ham.addEventListener('click', function(){
      var o = mnav.classList.toggle('open');
      if(mov) mov.classList.toggle('open', o);
      ham.classList.toggle('open', o);
      ham.setAttribute('aria-expanded', o ? 'true' : 'false');
    });
  }

  // ── Tabs / FAQ ────────────────────────────────────────────────
  window.showTab = function(id, btn){
    document.querySelectorAll('.tabpanel').forEach(function(p){ p.classList.remove('on'); });
    document.querySelectorAll('.tabbt').forEach(function(b){
      b.classList.remove('on'); b.setAttribute('aria-selected','false');
    });
    var p = document.getElementById(id);
    if(p) p.classList.add('on');
    if(btn){ btn.classList.add('on'); btn.setAttribute('aria-selected','true'); }
  };
  window.faqToggle = function(id){
    var el = document.getElementById(id);
    if(!el) return;
    var o = el.classList.toggle('open');
    var q = el.querySelector('.faq-q');
    if(q) q.setAttribute('aria-expanded', o ? 'true' : 'false');
  };

  // ── Today row highlight in schedule tables ─────────────────────
  var days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  var todayName = days[istNow().getDay()];
  document.querySelectorAll('table tbody tr').forEach(function(row){
    var td = row.querySelector('td');
    if(td && td.textContent.trim() === todayName) row.classList.add('tod');
  });

  // ── Share ─────────────────────────────────────────────────────
  window.shareResult = function(){
    if(navigator.share){
      navigator.share({title: document.title, url: location.href}).catch(function(){});
    } else if(navigator.clipboard){
      navigator.clipboard.writeText(location.href).then(function(){ alert('Link copied!'); });
    } else { prompt('Copy:', location.href); }
  };

  // ════════════════════════════════════════════════════════════
  //  OLD RESULT BANNER
  //  Jab tak aaj ka result nahi aata, purana dikhao + banner
  // ════════════════════════════════════════════════════════════
  function showOldBanner(rec, draw) {
    var old = document.getElementById('old-result-banner');
    if(old) old.remove();

    var card = document.getElementById('result-card');
    if(!card) return;

    // Calculate next draw time
    var h = istNow().getHours();
    var nextLabel = h < 13 ? '1:00 PM' : h < 18 ? '6:00 PM' : h < 20 ? '8:00 PM' : 'Tomorrow 1:00 PM';

    var banner = document.createElement('div');
    banner.id  = 'old-result-banner';
    banner.style.cssText =
      'background:linear-gradient(135deg,#f59e0b,#d97706);' +
      'color:#1a1a1a;padding:12px 16px;display:flex;' +
      'align-items:flex-start;justify-content:space-between;' +
      'gap:10px;flex-wrap:wrap;font-size:.82rem;font-weight:600;';

    banner.innerHTML =
      '<div style="display:flex;align-items:flex-start;gap:8px;flex:1;">' +
        '<span style="font-size:1.1rem;flex-shrink:0;">⏳</span>' +
        '<span><strong>' + draw + ' result abhi available nahi hai.</strong><br>' +
        'Showing last result: <strong>' + fmtDate(rec.date) + ' ' + rec.draw + '</strong>.<br>' +
        'Naya result ' + nextLabel + ' ke baad update hoga.</span>' +
      '</div>' +
      '<button onclick="location.reload()" style="' +
        'background:#fff;color:#1a1a1a;border:none;padding:5px 14px;' +
        'border-radius:20px;font-size:.78rem;font-weight:700;cursor:pointer;' +
        'flex-shrink:0;margin-top:2px;">🔄 Refresh</button>';

    // Insert at top of card (before card-hdr)
    card.insertBefore(banner, card.firstChild);
  }

  function clearBanner() {
    var b = document.getElementById('old-result-banner');
    if(b) b.remove();
  }

  // ════════════════════════════════════════════════════════════
  //  COUNTDOWN TIMER to next draw
  // ════════════════════════════════════════════════════════════
  function startCountdown() {
    var el = document.getElementById('countdown');
    if(!el) return;

    function update(){
      var n   = istNow();
      var sec = n.getHours()*3600 + n.getMinutes()*60 + n.getSeconds();
      var targets = [
        {label:'1PM draw', s:13*3600},
        {label:'6PM draw', s:18*3600},
        {label:'8PM draw', s:20*3600},
      ];
      var next = null;
      for(var i=0; i<targets.length; i++){
        if(targets[i].s > sec){ next = targets[i]; break; }
      }
      if(!next){ el.textContent = 'All draws done for today ✓'; return; }

      var diff = next.s - sec;
      var hh   = Math.floor(diff/3600);
      var mm   = Math.floor((diff%3600)/60);
      var ss   = diff%60;
      el.textContent = 'Next: ' + next.label + ' in ' +
        (hh>0 ? hh+'h ' : '') +
        String(mm).padStart(2,'0') + 'm ' +
        String(ss).padStart(2,'0') + 's';
    }
    update();
    setInterval(update, 1000);
  }
  startCountdown();

  // ════════════════════════════════════════════════════════════
  //  FIND RECORD: aaj ka result first, warna purana
  // ════════════════════════════════════════════════════════════
  function findRecord(data, state, draw) {
    var arr   = data[state] || [];
    var today = istDateStr();

    // 1. Exact match: today + draw
    for(var i=0; i<arr.length; i++){
      if(arr[i].date === today && arr[i].draw === draw)
        return { rec: arr[i], isToday: true };
    }
    // 2. Latest with same draw (fallback)
    for(var j=0; j<arr.length; j++){
      if(arr[j].draw === draw)
        return { rec: arr[j], isToday: false };
    }
    // 3. Absolute latest
    if(arr.length) return { rec: arr[0], isToday: false };
    return { rec: null, isToday: false };
  }

  // ════════════════════════════════════════════════════════════
  //  RENDER RESULT
  // ════════════════════════════════════════════════════════════
  function renderResult(rec, draw, isToday) {
    if(!rec){ showError(); return; }

    // ── Banner ──
    if(!isToday) showOldBanner(rec, draw);
    else         clearBanner();

    // ── Title + meta ──
    var dname    = rec.draw_name || ('Nagaland ' + rec.draw);
    var titleStr = dname + ' Result — ' + fmtDate(rec.date);

    var el = function(id){ return document.getElementById(id); };

    if(el('res-title'))   el('res-title').textContent   = titleStr;
    if(el('res-date'))    el('res-date').textContent     = fmtDate(rec.date) + ' · ' + rec.draw;
    if(el('res-source'))  el('res-source').textContent   = (rec.source||'').replace(/^https?:\/\//,'');
    if(el('last-updated'))el('last-updated').textContent =
      rec.fetched_at
        ? 'Fetched: ' + rec.fetched_at.replace('T',' ').replace('+05:30',' IST')
        : 'Date: ' + rec.date;

    var vb = el('verified-badge');
    if(vb){
      vb.style.display = 'inline-block';
      vb.textContent   = rec.verified ? '✓ Verified' : 'Unverified';
      vb.className     = rec.verified ? 'verified' : 'unverified';
    }

    // ── Image ──
    var imgUrl = rec.image || '';
    var imgEl  = el('res-img');
    var skelEl = el('img-skel');

    if(imgEl){
      if(imgUrl){
        imgEl.src = imgUrl;
        imgEl.alt = titleStr;
        imgEl.style.display = 'none'; // show on load
        // Update OG image
        var og = document.querySelector('meta[property="og:image"]');
        if(og) og.setAttribute('content', imgUrl);
      } else {
        // No image available
        if(skelEl) skelEl.style.display = 'none';
        var wrap = el('img-wrap');
        if(wrap) wrap.innerHTML =
          '<div style="padding:48px 20px;text-align:center;color:var(--muted);">' +
          '<div style="font-size:2rem;margin-bottom:12px;">⏰</div>' +
          '<p style="font-size:.9rem;font-weight:600;">Result image not yet published</p>' +
          '<p style="font-size:.8rem;margin-top:6px;">Please check back after ' + draw + ' draw time.</p>' +
          '</div>';
      }
    }

    // ── Download button → direct image link ──
    var dlBtn = el('dl-btn');
    if(dlBtn){
      if(imgUrl){
        dlBtn.href   = imgUrl;
        dlBtn.setAttribute('download', 'lottery-result-' + rec.date + '-' + draw + '.jpg');
        dlBtn.textContent = '⬇ Download Result Image';
        dlBtn.style.display = 'inline-flex';
      } else {
        dlBtn.style.display = 'none';
      }
    }

    // ── Source link ──
    var srcBtn = el('src-btn');
    if(srcBtn && rec.source){
      srcBtn.href = rec.source;
      srcBtn.style.display = 'inline-flex';
    }

    // ── SEO title update ──
    document.title = titleStr + ' | Lottery Sambad Result Today';
    var metaDesc = document.querySelector('meta[name="description"]');
    if(metaDesc) metaDesc.setAttribute('content',
      'Check ' + titleStr + '. Official result image updated automatically.');

    // ── Show card ──
    if(el('loading-state')) el('loading-state').style.display = 'none';
    if(el('error-state'))   el('error-state').style.display   = 'none';
    if(el('result-card'))   el('result-card').style.display   = 'block';
  }

  // ── Render history grid ────────────────────────────────────────
  function renderHistory(data) {
    var grid = document.getElementById('hist-grid');
    if(!grid) return;

    var items = [];
    ['nagaland','kerala'].forEach(function(st){
      (data[st]||[]).slice(0,10).forEach(function(r){ items.push({st:st, rec:r}); });
    });
    items.sort(function(a,b){
      var ka = a.rec.date + (a.rec.draw||'');
      var kb = b.rec.date + (b.rec.draw||'');
      return kb > ka ? 1 : -1;
    });
    items = items.slice(0,10);

    if(!items.length){
      grid.innerHTML = '<div style="grid-column:1/-1;padding:20px;text-align:center;color:var(--muted);">No history yet.</div>';
      return;
    }

    grid.innerHTML = items.map(function(it){
      var r   = it.rec;
      var img = r.image || '';
      var nm  = (r.draw_name||it.st+' '+r.draw).replace(/^Dear\s/,'');
      return '<a class="hitem" href="' + (img||'#') + '" ' + (img ? 'target="_blank" rel="noopener"' : '') + '>' +
        '<span>' + nm + ' ' + (r.draw||'') + '</span>' +
        '<span class="hitem-sub">' + fmtDate(r.date) + '</span>' +
        '<span class="hbadge">' + it.st.toUpperCase() + '</span>' +
        '</a>';
    }).join('');
  }

  // ── Render sidebar ─────────────────────────────────────────────
  function renderSidebar(data) {
    var list = document.getElementById('sidebar-list');
    if(!list) return;
    var dc = ['','b','g','r','','b'];
    var k = 0, items = [];
    (data.nagaland||[]).slice(0,4).forEach(function(r){
      items.push({lbl:'Nagaland '+r.draw, sub:fmtDate(r.date), d:dc[k++%6]});
    });
    (data.kerala||[]).slice(0,2).forEach(function(r){
      items.push({lbl:'Kerala '+(r.draw_name||r.draw||'3PM'), sub:fmtDate(r.date), d:dc[k++%6]});
    });
    list.innerHTML = items.map(function(it){
      return '<li><a class="sri" href="#"><span class="dot '+it.d+'"></span>' +
        '<span class="si"><span class="sn">'+it.lbl+'</span>' +
        '<span class="st">'+it.sub+'</span></span>' +
        '<span class="sa">›</span></a></li>';
    }).join('');
  }

  // ── Error state ────────────────────────────────────────────────
  function showError() {
    var el = function(id){ return document.getElementById(id); };
    if(el('loading-state')) el('loading-state').style.display = 'none';
    if(el('result-card'))   el('result-card').style.display   = 'none';
    if(el('error-state'))   el('error-state').style.display   = 'block';
  }

  // ════════════════════════════════════════════════════════════
  //  MAIN FETCH with cache-bust (fixes stale date bug)
  // ════════════════════════════════════════════════════════════
  function loadData() {
    var bust = '?t=' + Date.now();  // Force fresh fetch every time
    var ctrl = new AbortController();
    var to   = setTimeout(function(){ ctrl.abort(); }, 10000);

    fetch(JSON_URL + bust, { signal: ctrl.signal, cache: 'no-store' })
      .then(function(r){
        clearTimeout(to);
        if(!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function(data){
        var draw  = CFG.draw  || detectDraw();
        var state = CFG.state || 'nagaland';
        var found = findRecord(data, state, draw);

        renderResult(found.rec, draw, found.isToday);
        renderHistory(data);
        renderSidebar(data);
      })
      .catch(function(err){
        clearTimeout(to);
        console.warn('JSON fetch failed:', err.message);
        // Show error only if first load failed
        var card = document.getElementById('result-card');
        if(card && card.style.display === 'none'){
          showError();
        }
      });
  }

  // ── Image load handlers ────────────────────────────────────────
  // These are called from img onload/onerror in HTML
  window.onImgLoad = function(img) {
    img.style.display = 'block';
    var skel = document.getElementById('img-skel');
    if(skel) skel.style.display = 'none';
  };
  window.onImgFail = function(img) {
    img.style.display = 'none';
    var skel = document.getElementById('img-skel');
    if(skel) skel.style.display = 'none';
    var wrap = document.getElementById('img-wrap');
    if(wrap && !wrap.querySelector('.img-err')){
      var div = document.createElement('div');
      div.className = 'img-err';
      div.style.cssText = 'padding:40px;text-align:center;color:var(--muted);font-size:.85rem;';
      div.innerHTML = '⏰ Image not available yet.<br>Please check after draw time.';
      wrap.appendChild(div);
    }
  };

  // ── Auto-refresh schedule ──────────────────────────────────────
  function scheduleNext() {
    var h = istNow().getHours();
    var m = istNow().getMinutes();

    // Near draw times: every 3 minutes
    var nearDraw =
      (h === 12 && m >= 50) || (h === 13 && m <= 20) ||
      (h === 17 && m >= 50) || (h === 18 && m <= 20) ||
      (h === 19 && m >= 50) || (h === 20 && m <= 20);

    setTimeout(function(){
      loadData();
      scheduleNext();
    }, nearDraw ? 3*60*1000 : 10*60*1000);
  }

  // ── INIT ──────────────────────────────────────────────────────
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', function(){ loadData(); scheduleNext(); });
  } else {
    loadData();
    scheduleNext();
  }

})();
