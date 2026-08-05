// Promo Threads — Client App v3
(function() {
  let allPromos = [];
  let expiredPromos = [];
  let activeCategory = 'semua';
  let searchQuery = '';
  let sortMode = 'terbaru';
  let providerFilter = '';
  let typeFilter = '';
  let showBookmarkOnly = false;
  let visibleCount = 20;
  let bookmarks = JSON.parse(localStorage.getItem('pt-bookmarks') || '[]');

  const $ = id => document.getElementById(id);
  const grid = $('promoGrid'), skeletonGrid = $('skeletonGrid');
  const countEl = $('promoCount'), emptyEl = $('emptyState');
  const searchInput = $('searchInput'), lastUpdatedEl = $('lastUpdated');
  const heroStats = $('heroStats'), sortSelect = $('sortSelect');
  const providerSelect = $('providerFilter'), scrollTopBtn = $('scrollTop');
  const themeToggle = $('themeToggle'), savedBtn = $('savedBtn');
  const savedCount = $('savedCount'), loadMoreBtn = $('loadMoreBtn');
  const trendingSection = $('trendingGrid');
  const typeSelect = $('typeFilter');
  const todaySection = $('todaySection'), todayGrid = $('todayGrid');
  const statsGrid = $('statsGrid');
  const archiveSection = $('archiveSection'), archiveGrid = $('archiveGrid');
  const modalOverlay = $('modalOverlay'), modalContent = $('modalContent');

  const catLabels = {
    makanan:'🍔 Makanan', belanja:'🛍️ Belanja', hiburan:'🎬 Hiburan',
    hotel:'🏨 Hotel', transport:'🚗 Transport', kesehatan:'💊 Kesehatan',
    keuangan:'💳 Keuangan', lainnya:'📦 Lainnya',
  };

  // Theme
  const savedTheme = localStorage.getItem('pt-theme') || 'dark';
  if (savedTheme === 'light') document.body.classList.add('light');
  themeToggle.textContent = savedTheme === 'light' ? '🌙' : '☀️';
  themeToggle.addEventListener('click', () => {
    document.body.classList.toggle('light');
    const isLight = document.body.classList.contains('light');
    localStorage.setItem('pt-theme', isLight ? 'light' : 'dark');
    themeToggle.textContent = isLight ? '🌙' : '☀️';
  });

  // Date parser
  function parseDate(str) {
    if (!str) return null;
    const months = {januari:0,februari:1,maret:2,april:3,mei:4,juni:5,juli:6,agustus:7,september:8,oktober:9,november:10,desember:11};
    const m = str.match(/(\d{1,2})\s+(\w+)\s+(\d{4})/);
    if (m) { const mon = months[m[2].toLowerCase()]; if (mon !== undefined) return new Date(+m[3], mon, +m[1]); }
    const m2 = str.match(/(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})/);
    if (m2) return new Date(+m2[3], +m2[2]-1, +m2[1]);
    return null;
  }
  function getCountdown(str) {
    const d = parseDate(str); if (!d) return null;
    const diff = Math.ceil((d - new Date()) / 86400000);
    if (diff < 0) return null;
    if (diff === 0) return '⚡ Hari terakhir!';
    if (diff <= 7) return `⏰ Sisa ${diff} hari`;
    return null;
  }
  function isExpired(str) {
    const d = parseDate(str); return d && d < new Date().setHours(0,0,0,0);
  }
  function isNew(t) { return t && (Date.now() - new Date(t).getTime()) < 86400000; }
  function isToday(t) { return t && (Date.now() - new Date(t).getTime()) < 86400000; }
  function getPromoType(p) {
    const t = (p.text||'').toLowerCase();
    if (p.code) return 'voucher';
    if (t.includes('cashback')) return 'cashback';
    if (t.includes('gratis') || t.includes('free')) return 'gratis';
    if (p.discount) return 'diskon';
    return '';
  }

  // Load data
  async function loadData() {
    try {
      const [pr, mr] = await Promise.all([fetch('/data/promos.json'), fetch('/data/meta.json')]);
      if (pr.ok) { const all = await pr.json();
        allPromos = all.filter(p => !isExpired(p.valid_until));
        expiredPromos = all.filter(p => isExpired(p.valid_until));
      }
      if (mr.ok) { const meta = await mr.json();
        if (meta.last_updated) { const d = new Date(meta.last_updated);
          lastUpdatedEl.textContent = `Update: ${d.toLocaleDateString('id-ID',{day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'})}`;
        }
      }
    } catch(e) { console.warn(e); }
    const providers = [...new Set(allPromos.map(p => p.source))].sort();
    providers.forEach(prov => { const o = document.createElement('option'); o.value = prov; o.textContent = prov; providerSelect.appendChild(o); });
    heroStats.textContent = `🔥 ${allPromos.length} promo aktif hari ini`;
    updateSavedCount();
    renderToday();
    renderStats();
    renderTrending();
    renderArchive();
    skeletonGrid.style.display = 'none';
    grid.style.display = '';
    render();
  }

  // Promo Hari Ini
  function renderToday() {
    const today = allPromos.filter(p => isToday(p.scraped_at)).slice(0, 3);
    if (!today.length) { todaySection.style.display = 'none'; return; }
    todaySection.style.display = '';
    todayGrid.innerHTML = today.map(p => `
      <div class="today-card" onclick="openDetail('${p.id}')">
        <div class="today-source">${p.source}</div>
        <div class="today-text">${escapeHtml((p.text||'').slice(0,80))}...</div>
        ${p.discount ? `<span class="tag tag-discount">${p.discount}</span>` : ''}
        ${p.code ? `<span class="tag tag-code">📋 ${p.code}</span>` : ''}
      </div>`).join('');
  }

  // Stats Dashboard
  function renderStats() {
    const counts = {};
    Object.keys(catLabels).forEach(c => counts[c] = 0);
    allPromos.forEach(p => { if (counts[p.category] !== undefined) counts[p.category]++; else counts['lainnya']++; });
    const max = Math.max(...Object.values(counts), 1);
    statsGrid.innerHTML = Object.entries(counts).filter(([,v]) => v > 0).sort((a,b) => b[1]-a[1]).map(([cat, count]) => `
      <div class="stat-row">
        <span class="stat-label">${catLabels[cat]||cat}</span>
        <div class="stat-bar-wrap"><div class="stat-bar" style="width:${(count/max)*100}%"></div></div>
        <span class="stat-num">${count}</span>
      </div>`).join('');
  }

  // Trending
  function renderTrending() {
    if (!bookmarks.length) { trendingSection.parentElement.style.display = 'none'; return; }
    trendingSection.parentElement.style.display = '';
    const trending = allPromos.filter(p => bookmarks.includes(p.id)).slice(0, 5);
    if (!trending.length) { trendingSection.parentElement.style.display = 'none'; return; }
    trendingSection.innerHTML = trending.map(p => `
      <div class="trending-card" onclick="openDetail('${p.id}')">
        <span class="source">${p.source}</span>
        <span class="trending-text">${escapeHtml((p.text||'').slice(0,60))}...</span>
        ${p.discount ? `<span class="tag tag-discount">${p.discount}</span>` : ''}
      </div>`).join('');
  }

  // Archive
  function renderArchive() {
    if (!expiredPromos.length) { archiveSection.style.display = 'none'; return; }
    archiveSection.style.display = '';
    archiveGrid.innerHTML = expiredPromos.slice(0, 10).map(p => `
      <div class="archive-card">
        <span class="source">${p.source}</span>
        <span class="archive-text">${escapeHtml((p.text||'').slice(0,60))}...</span>
        <span class="tag tag-expired">Expired</span>
      </div>`).join('');
  }

  // Main render
  function render() {
    let filtered = allPromos;
    if (showBookmarkOnly) filtered = filtered.filter(p => bookmarks.includes(p.id));
    if (activeCategory !== 'semua') filtered = filtered.filter(p => p.category === activeCategory);
    if (providerFilter) filtered = filtered.filter(p => p.source === providerFilter);
    if (typeFilter) filtered = filtered.filter(p => getPromoType(p) === typeFilter);
    if (searchQuery) { const q = searchQuery.toLowerCase();
      filtered = filtered.filter(p => (p.text||'').toLowerCase().includes(q) || (p.source||'').toLowerCase().includes(q) || (p.code||'').toLowerCase().includes(q));
    }
    if (sortMode === 'diskon') filtered.sort((a,b) => (parseInt((b.discount||'0').replace(/\D/g,''))||0) - (parseInt((a.discount||'0').replace(/\D/g,''))||0));
    else filtered.sort((a,b) => (b.scraped_at||'').localeCompare(a.scraped_at||''));

    countEl.textContent = `${filtered.length} promo ditemukan`;
    if (!filtered.length) { grid.innerHTML = ''; emptyEl.style.display = 'block'; loadMoreBtn.style.display = 'none'; return; }
    emptyEl.style.display = 'none';
    const visible = filtered.slice(0, visibleCount);
    loadMoreBtn.style.display = filtered.length > visibleCount ? '' : 'none';

    grid.innerHTML = visible.map((p, idx) => {
      const tags = [];
      if (p.discount) tags.push(`<span class="tag tag-discount">${p.discount}</span>`);
      if (p.code) tags.push(`<span class="tag tag-code" onclick="event.stopPropagation();copyCode('${p.code}',this)" title="Klik copy">📋 ${p.code}</span>`);
      const cd = getCountdown(p.valid_until);
      if (cd) tags.push(`<span class="tag tag-countdown">${cd}</span>`);
      else if (p.valid_until) tags.push(`<span class="tag tag-valid">s/d ${p.valid_until}</span>`);
      const isB = bookmarks.includes(p.id);
      const catLabel = catLabels[p.category] || p.category;
      const newBadge = isNew(p.scraped_at) ? '<span class="badge-new">BARU</span>' : '';
      const textShort = (p.text||'').length > 150;

      return `
        <div class="promo-card card-animate" style="animation-delay:${idx*0.03}s" onclick="openDetail('${p.id}')">
          <div class="card-header">
            <span class="source">${p.source||'Unknown'} ${newBadge}</span>
            <span class="category-badge">${catLabel}</span>
          </div>
          <div class="card-text ${textShort?'truncated':''}" id="text-${p.id}">${escapeHtml(p.text||'')}</div>
          ${textShort ? `<button class="expand-btn" onclick="event.stopPropagation();toggleExpand('text-${p.id}',this)">Selengkapnya ↓</button>` : ''}
          ${tags.length ? `<div class="card-tags">${tags.join('')}</div>` : ''}
          <div class="card-footer">
            <span class="time">${p.scraped_at ? getTimeAgo(new Date(p.scraped_at)) : ''}</span>
            <div class="card-actions">
              <button class="action-btn" onclick="event.stopPropagation();toggleBookmark('${p.id}')" title="${isB?'Hapus':'Simpan'}">${isB?'❤️':'🤍'}</button>
              <button class="action-btn" onclick="event.stopPropagation();shareWA('${escapeHtml((p.text||'').slice(0,80))}','${p.source_url||''}')" title="WhatsApp">💬</button>
              <button class="action-btn" onclick="event.stopPropagation();shareTG('${escapeHtml((p.text||'').slice(0,80))}','${p.source_url||''}')" title="Telegram">✈️</button>
              <button class="action-btn" onclick="event.stopPropagation();shareX('${escapeHtml((p.text||'').slice(0,80))}','${p.source_url||''}')" title="X/Twitter">𝕏</button>
            </div>
          </div>
        </div>`;
    }).join('');
  }

  // Helpers
  function escapeHtml(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;').replace(/`/g,'&#96;'); }
  function getTimeAgo(d) { const s=(Date.now()-d.getTime())/1000; if(s<3600)return`${Math.floor(s/60)}m lalu`; if(s<86400)return`${Math.floor(s/3600)}j lalu`; if(s<604800)return`${Math.floor(s/86400)}h lalu`; return d.toLocaleDateString('id-ID',{day:'numeric',month:'short'}); }
  function updateSavedCount() { savedCount.textContent = bookmarks.length||''; savedCount.style.display = bookmarks.length?'':'none'; }

  // Global functions
  window.copyCode = function(code, el) { navigator.clipboard.writeText(code); const o=el.innerHTML; el.innerHTML='✅ Copied!'; el.classList.add('copied'); setTimeout(()=>{el.innerHTML=o;el.classList.remove('copied');},1500); };
  window.toggleBookmark = function(id) { const i=bookmarks.indexOf(id); if(i>-1)bookmarks.splice(i,1);else bookmarks.push(id); localStorage.setItem('pt-bookmarks',JSON.stringify(bookmarks)); updateSavedCount(); renderTrending(); render(); };
  window.shareWA = function(t,u) { window.open(`https://wa.me/?text=${encodeURIComponent(`Promo: ${t}... ${u}`)}`, '_blank'); };
  window.shareTG = function(t,u) { window.open(`https://t.me/share/url?url=${encodeURIComponent(u)}&text=${encodeURIComponent(`Promo: ${t}`)}`, '_blank'); };
  window.shareX = function(t,u) { window.open(`https://x.com/intent/tweet?text=${encodeURIComponent(`Promo: ${t}`)}&url=${encodeURIComponent(u)}`, '_blank'); };
  window.toggleExpand = function(id, btn) { const el=document.getElementById(id); el.classList.toggle('truncated'); btn.textContent = el.classList.contains('truncated') ? 'Selengkapnya ↓' : 'Lebih sedikit ↑'; };

  // Detail modal
  window.openDetail = function(id) {
    const p = allPromos.find(x => x.id === id) || expiredPromos.find(x => x.id === id);
    if (!p) return;
    const tags = [];
    if (p.discount) tags.push(`<span class="tag tag-discount">${p.discount}</span>`);
    if (p.code) tags.push(`<span class="tag tag-code" onclick="copyCode('${p.code}',this)">📋 Kode: ${p.code}</span>`);
    if (p.valid_until) tags.push(`<span class="tag tag-valid">Berlaku s/d ${p.valid_until}</span>`);
    const cd = getCountdown(p.valid_until);
    if (cd) tags.push(`<span class="tag tag-countdown">${cd}</span>`);

    modalContent.innerHTML = `
      <button class="modal-close" onclick="closeDetail()">✕</button>
      <div class="modal-header"><span class="source">${p.source}</span><span class="category-badge">${catLabels[p.category]||p.category}</span></div>
      <div class="modal-body">${escapeHtml(p.text||'')}</div>
      ${tags.length ? `<div class="modal-tags">${tags.join('')}</div>` : ''}
      <div class="modal-actions">
        <button onclick="shareWA('${escapeHtml((p.text||'').slice(0,80))}','${p.source_url||''}')">💬 WhatsApp</button>
        <button onclick="shareTG('${escapeHtml((p.text||'').slice(0,80))}','${p.source_url||''}')">✈️ Telegram</button>
        <button onclick="shareX('${escapeHtml((p.text||'').slice(0,80))}','${p.source_url||''}')">𝕏 Twitter</button>
        ${p.source_url && p.source_url!=='#' ? `<a href="${p.source_url}" target="_blank" rel="noopener">🔗 Sumber</a>` : ''}
      </div>`;
    modalOverlay.style.display = 'flex';
  };
  window.closeDetail = function() { modalOverlay.style.display = 'none'; };
  modalOverlay.addEventListener('click', e => { if (e.target === modalOverlay) closeDetail(); });

  // Events
  $('catPills').addEventListener('click', e => { const b=e.target.closest('.pill'); if(!b)return; document.querySelectorAll('.pill').forEach(p=>p.classList.remove('active')); b.classList.add('active'); activeCategory=b.dataset.cat; visibleCount=20; render(); });
  searchInput.addEventListener('input', e => { searchQuery=e.target.value.trim(); visibleCount=20; render(); });
  sortSelect.addEventListener('change', e => { sortMode=e.target.value; render(); });
  providerSelect.addEventListener('change', e => { providerFilter=e.target.value; render(); });
  typeSelect.addEventListener('change', e => { typeFilter=e.target.value; render(); });
  savedBtn.addEventListener('click', () => { showBookmarkOnly=!showBookmarkOnly; savedBtn.classList.toggle('active',showBookmarkOnly); visibleCount=20; render(); });
  loadMoreBtn.addEventListener('click', () => { visibleCount+=20; render(); });
  window.addEventListener('scroll', () => { scrollTopBtn.classList.toggle('visible', window.scrollY>400); });
  scrollTopBtn.addEventListener('click', () => window.scrollTo({top:0,behavior:'smooth'}));

  // Init
  loadData();
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(()=>{});
})();
