/**
 * app.js — Lottery Result Frontend
 * Image path: images/nagaland-8pm-2026-04-13.jpg (GitHub hosted)
 * Raw URL:    RAW_BASE + image path
 */
(function () {
  'use strict';

  // ── CHANGE THESE 2 URLS ──────────────────────────────────
  var SITE_BASE = 'https://harshsharmaoo7.github.io/Lottery-Bot/';
  var RAW_BASE  = 'https://raw.githubusercontent.com/harshsharmaOO7/Lottery-Bot/main/';
  // ─────────────────────────────────────────────────────────

  var JSON_URL = SITE_BASE + 'results.json';
  var CFG      = window.PAGE_CONFIG || { draw: null, state: 'nagaland' };

  // ── IST helpers ──────────────────────────────────────────
  function istNow() {
    return new Date(Date.now() + 19800000 + new Date().getTimezoneOffset() * 60000);
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
    return h < 13 ? '1PM' : h < 18 ? '6PM' : '8PM';
  }

  // ── Clock ────────────────────────────────────────────────
  function tick() {
    var el = document.getElementById('clock');
    if (!el) return;
    var n = istNow(), h = n.getHours(), mi = n.getMinutes(), s = n.getSeconds();
    var ampm = h < 12 ? 'AM' : 'PM';
    el.textContent = (h%12||12) + ':' + String(mi).padStart(2,'0') + ':' +
      String(s).padStart(2,'0') + ' ' + ampm + ' IST';
  }
  tick(); setInterval(tick, 1000);
  var yr = document.getElementById('yr');
  if (yr) yr.textContent = new Date().getFullYear();

  // ── Dark mode ────────────────────────────────────────────
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
    dark = !dark; localStorage.setItem('theme', dark?'dark':'light'); applyTheme();
  });

  // ── Hamburger ────────────────────────────────────────────
  var ham = document.getElementById('hamBtn');
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
      ham.setAttribute('aria-expanded', o?'true':'false');
    });
  }

  // ── Tabs / FAQ ───────────────────────────────────────────
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
    if(q) q.setAttribute('aria-expanded', o?'true':'false');
  };

  // ── Today row in tables ──────────────────────────────────
  var days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  document.querySelectorAll('table tbody tr').forEach(function(row){
    var td = row.querySelector('td');
    if(td && td.textContent.trim() === days[istNow().getDay()])
      row.classList.add('tod');
  });

  // ── Share ────────────────────────────────────────────────
  window.shareResult = function(){
    if(navigator.share) navigator.share({title:document.title,url:location.href}).catch(function(){});
    else if(navigator.clipboard) navigator.clipboard.writeText(location.href)
      .then(function(){ alert('Link copied!'); });
    else prompt('Copy:', location.href);
  };

  // ── Image URL builder ────────────────────────────────────
  // image field can be:
  //   "images/nagaland-8pm-2026-04-13.jpg"  → use RAW_BASE
  //   "https://..."                          → use as-is
  //   ""                                     → no image
  function buildImgUrl(rec) {
    var img = rec.image || '';
    if (!img) return '';
    if (img.startsWith('http')) return img;          // already absolute
    return RAW_BASE + img;                           // relative → raw GitHub
  }

  // ── Old result banner ────────────────────────────────────
  function showOldBanner(rec, draw) {
    var old = document.getElementById('old-banner');
    if (old) old.remove();
    var card = document.getElementById('result-card');
    if (!card) return;
    var h = istNow().getHours();
    var next = h < 13 ? '1:00 PM' : h < 18 ? '6:00 PM' : h < 20 ? '8:00 PM' : 'kal 1:00 PM';
    var b = document.createElement('div');
    b.id = 'old-banner';
    b.style.cssText =
      'background:linear-gradient(135deg,#f59e0b,#d97706);color:#1a1a1a;' +
      'padding:12px 16px;display:flex;align-items:flex-start;justify-content:space-between;' +
      'gap:10px;flex-wrap:wrap;font-size:.82rem;font-weight:600;';
    b.innerHTML =
      '<div style="display:flex;align-items:flex-start;gap:8px;flex:1;">' +
        '<span style="font-size:1.1rem;flex-shrink:0;">⏳</span>' +
        '<span><strong>' + draw + ' ka naya result abhi nahi aaya.</strong><br>' +
        'Last result dikh raha hai: <strong>' + fmtDate(rec.date) + ' · ' + rec.draw + '</strong><br>' +
        'Naya result <strong>' + next + '</strong> ke baad update hoga.</span>' +
      '</div>' +
      '<button onclick="location.reload()" style="background:#fff;color:#1a1a1a;border:none;' +
        'padding:5px 14px;border-radius:20px;font-size:.78rem;font-weight:700;cursor:pointer;' +
        'flex-shrink:0;margin-top:2px;">🔄 Refresh</button>';
    card.insertBefore(b, card.firstChild);
  }

  // ── Countdown ────────────────────────────────────────────
  function startCountdown() {
    var el = document.getElementById('countdown');
    if (!el) return;
    function update(){
      var n = istNow();
      var sec = n.getHours()*3600 + n.getMinutes()*60 + n.getSeconds();
      var targets = [{l:'1PM',s:13*3600},{l:'6PM',s:18*3600},{l:'8PM',s:20*3600}];
      var next = null;
      for(var i=0;i<targets.length;i++){ if(targets[i].s>sec){next=targets[i];break;} }
      if(!next){ el.textContent='Aaj ke sabhi draws ho gaye ✓'; return; }
      var d=next.s-sec, hh=Math.floor(d/3600), mm=Math.floor((d%3600)/60), ss=d%60;
      el.textContent='Next: '+next.l+' draw in '+(hh>0?hh+'h ':'')+
        String(mm).padStart(2,'0')+'m '+String(ss).padStart(2,'0')+'s';
    }
    update(); setInterval(update,1000);
  }
  startCountdown();

  // ── Find record ──────────────────────────────────────────
  function findRecord(data, state, draw) {
    var arr = data[state] || [];
    var today = istDateStr();
    // 1. Today + exact draw
    for(var i=0;i<arr.length;i++)
      if(arr[i].date===today && arr[i].draw===draw)
        return {rec:arr[i], isToday:true};
    // 2. Latest with same draw (old result fallback)
    for(var j=0;j<arr.length;j++)
      if(arr[j].draw===draw)
        return {rec:arr[j], isToday:false};
    // 3. Absolute latest
    if(arr.length) return {rec:arr[0], isToday:false};
    return {rec:null, isToday:false};
  }

  // ── Render result ────────────────────────────────────────
  function renderResult(rec, draw, isToday) {
    if (!rec) { showError(); return; }

    if (!isToday) showOldBanner(rec, draw);
    else {
      var b = document.getElementById('old-banner');
      if (b) b.remove();
    }

    var dname = rec.draw_name || ('Nagaland '+rec.draw);
    var titleStr = dname + ' Result — ' + fmtDate(rec.date);
    var E = function(id){ return document.getElementById(id); };

    if(E('res-title'))    E('res-title').textContent   = titleStr;
    if(E('res-date'))     E('res-date').textContent     = fmtDate(rec.date)+' · '+rec.draw;
    if(E('res-source'))   E('res-source').textContent   = (rec.source||'').replace(/^https?:\/\//,'');
    if(E('last-updated')) E('last-updated').textContent =
      rec.fetched_at
        ? 'Fetched: '+rec.fetched_at.replace('T',' ').replace('+05:30',' IST')
        : 'Date: '+rec.date;
    var vb = E('verified-badge');
    if(vb){
      vb.style.display='inline-block';
      vb.textContent = rec.verified?'✓ Verified':'Unverified';
      vb.className   = rec.verified?'verified':'unverified';
    }

    // ── Image — uses RAW_BASE for GitHub-hosted images ──
    var iu = buildImgUrl(rec);
    var imgEl = E('res-img');
    var skelEl = E('img-skel');
    if (imgEl) {
      if (iu) {
        imgEl.src = iu;
        imgEl.alt = titleStr;
        imgEl.style.display = 'none';
      } else {
        if (skelEl) skelEl.style.display = 'none';
        var wrap = E('img-wrap');
        if (wrap) wrap.innerHTML =
          '<div style="padding:48px 20px;text-align:center;color:var(--muted);">' +
          '<div style="font-size:2rem;margin-bottom:12px;">📸</div>' +
          '<p style="font-weight:600;">Result image abhi available nahi hai</p>' +
          '<p style="font-size:.8rem;margin-top:6px;opacity:.7;">'+draw+' draw ke baad yahan dikhai degi</p>' +
          '</div>';
      }
    }

    // ── Buttons ──
    var dlBtn = E('dl-btn');
    if (dlBtn) {
      if (iu) {
        dlBtn.href = iu;
        dlBtn.setAttribute('download','lottery-result-'+rec.date+'-'+draw+'.jpg');
        dlBtn.style.display='inline-flex';
      } else {
        dlBtn.style.display='none';
      }
    }
    var srcBtn = E('src-btn');
    if (srcBtn && rec.source) { srcBtn.href=rec.source; srcBtn.style.display='inline-flex'; }

    // SEO title
    document.title = titleStr+' | Lottery Sambad Result Today';

    // Show card
    if(E('loading-state')) E('loading-state').style.display='none';
    if(E('error-state'))   E('error-state').style.display='none';
    if(E('result-card'))   E('result-card').style.display='block';
  }

  // ── Image onload/onerror ─────────────────────────────────
  window.onImgLoad = function(img){
    img.style.display='block';
    var sk=document.getElementById('img-skel');
    if(sk) sk.style.display='none';
  };
  window.onImgFail = function(img){
    img.style.display='none';
    var sk=document.getElementById('img-skel');
    if(sk) sk.style.display='none';
    var wrap=document.getElementById('img-wrap');
    if(wrap && !wrap.querySelector('.img-err')){
      var d=document.createElement('div');
      d.className='img-err';
      d.style.cssText='padding:40px;text-align:center;color:var(--muted);font-size:.85rem;';
      d.innerHTML='⚠️ Image load nahi hui.<br><small style="opacity:.7">Image abhi upload nahi hui hai</small>';
      wrap.appendChild(d);
    }
  };

  // ── Render history ───────────────────────────────────────
  function renderHistory(data) {
    var grid = document.getElementById('hist-grid');
    if (!grid) return;
    var items = [];
    ['nagaland','kerala'].forEach(function(st){
      (data[st]||[]).slice(0,10).forEach(function(r){ items.push({st:st,rec:r}); });
    });
    items.sort(function(a,b){
      return (b.rec.date+b.rec.draw)>(a.rec.date+a.rec.draw)?1:-1;
    });
    items = items.slice(0,10);
    if (!items.length) {
      grid.innerHTML='<div style="grid-column:1/-1;padding:20px;text-align:center;color:var(--muted);">No history yet.</div>';
      return;
    }
    grid.innerHTML = items.map(function(it){
      var r=it.rec, iu=buildImgUrl(r);
      var nm=(r.draw_name||it.st+' '+r.draw).replace(/^Dear\s/,'');
      return '<a class="hitem" href="'+(iu||'#')+'" '+(iu?'target="_blank" rel="noopener"':'')+'>'+
        '<span>'+nm+' '+r.draw+'</span>'+
        '<span class="hitem-sub">'+fmtDate(r.date)+'</span>'+
        '<span class="hbadge">'+it.st.toUpperCase()+'</span>'+
        '</a>';
    }).join('');
  }

  // ── Render sidebar ───────────────────────────────────────
  function renderSidebar(data) {
    var list = document.getElementById('sidebar-list');
    if (!list) return;
    var dc=['','b','g','r','','b'], k=0, items=[];
    (data.nagaland||[]).slice(0,4).forEach(function(r){
      items.push({lbl:'Nagaland '+r.draw,sub:fmtDate(r.date),d:dc[k++%6]});
    });
    (data.kerala||[]).slice(0,2).forEach(function(r){
      items.push({lbl:'Kerala '+(r.draw_name||r.draw||'3PM'),sub:fmtDate(r.date),d:dc[k++%6]});
    });
    list.innerHTML = items.map(function(it){
      return '<li><a class="sri" href="#"><span class="dot '+it.d+'"></span>'+
        '<span class="si"><span class="sn">'+it.lbl+'</span>'+
        '<span class="st">'+it.sub+'</span></span>'+
        '<span class="sa">›</span></a></li>';
    }).join('');
  }

  // ── Error state ──────────────────────────────────────────
  function showError() {
    var E=function(id){return document.getElementById(id);};
    if(E('loading-state')) E('loading-state').style.display='none';
    if(E('result-card'))   E('result-card').style.display='none';
    if(E('error-state'))   E('error-state').style.display='block';
  }

  // ── Fetch JSON (cache-bust fixes stale date) ─────────────
  function loadData() {
    var bust = '?t=' + Date.now();
    var ctrl = new AbortController();
    var to   = setTimeout(function(){ ctrl.abort(); }, 10000);
    fetch(JSON_URL + bust, { signal: ctrl.signal, cache: 'no-store' })
      .then(function(r){ clearTimeout(to); if(!r.ok) throw new Error('HTTP '+r.status); return r.json(); })
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
        var card = document.getElementById('result-card');
        if (card && card.style.display==='none') showError();
      });
  }

  // ── Auto-refresh schedule ────────────────────────────────
  function scheduleNext() {
    var h=istNow().getHours(), m=istNow().getMinutes();
    var near = (h===12&&m>=50)||(h===13&&m<=20)||
               (h===17&&m>=50)||(h===18&&m<=20)||
               (h===19&&m>=50)||(h===20&&m<=20);
    setTimeout(function(){ loadData(); scheduleNext(); }, near?3*60*1000:10*60*1000);
  }

  if (document.readyState==='loading')
    document.addEventListener('DOMContentLoaded', function(){ loadData(); scheduleNext(); });
  else { loadData(); scheduleNext(); }

})();
