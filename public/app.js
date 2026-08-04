// Promo Threads — Client App (Full Featured)
(function() {
  let allPromos = [];
  let activeCategory = 'semua';
  let searchQuery = '';
  let sortMode = 'terbaru';
  let providerFilter = '';
  let bookmarks = JSON.parse(localStorage.getItem('pt-bookmarks') || '[]');

  const grid = document.getElementById('promoGrid');
  const skeletonGrid = document.getElementById('skeletonGrid');
  const countEl = document.getElementById('promoCount');
  const emptyEl = document.getElementById('emptyState');
  const searchInput = document.getElementById('searchInput');
  const lastUpdatedEl = document.getElementById('lastUpdated');
  const heroStats = document.getElementById('heroStats');
  const sortSelect = document.getElementById('sortSelect');
  const providerSelect = document.getElementById('providerFilter');
  const scrollTopBtn = document.getElementById('scrollTop');
  const themeToggle = document.getElementById('themeToggle');

  const catLabels = {
    makanan:'🍔 Makanan', belanja:'🛍️ Belanja', hiburan:'🎬 Hiburan',
    hotel:'🏨 Hotel', transport:'🚗 Transport', kesehatan:'💊 Kesehatan',
    keuangan:'💳 Keuangan', lainnya:'📦 Lainnya',
  };

  // ─── Theme ────────────────────────────────────────────────────────────────────
  const savedTheme = localStorage.getItem('pt-theme') || 'dark';
  if (savedTheme === 'light') document.body.classList.add('light');
  themeToggle.textContent = savedTheme === 'light' ? '🌙' : '☀️';

  themeToggle.addEventListener('click', () => {
    document.body.classList.toggle('light');
    const isLight = document.body.classList.contains('light');
    localStorage.setItem('pt-theme', isLight ? 'light' : 'dark');
    themeToggle.textContent = isLight ? '🌙' : '☀️';
  });

  // ─── Date parser ──────────────────────────────────────────────────────────────
  function parseIndonesianDate(str) {
    if (!str) return null;
    const months = {januari:0,februari:1,maret:2,april:3,mei:4,juni:5,juli:6,agustus:7,september:8,oktober:9,november:10,desember:11};
    const m = str.match(/(\d{1,2})\s+(\w+)\s+(\d{4})/);
    if (m) { const mon = months[m[2].toLowerCase()]; if (mon !== undefined) return new Date(+m[3], mon, +m[1]); }
    const m2 = str.match(/(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})/);
    if (m2) return new Date(+m2[3], +m2[2]-1, +m2[1]);
    return null;
  }

  // ─── Load data ────────────────────────────────────────────────────────────────
  async function loadData() {
    try {
      const [promosRes, metaRes] = await Promise.all([
        fetch('/data/promos.json'), fetch('/data/meta.json'),
      ]);
      if (promosRes.ok) allPromos = await promosRes.json();
      if (metaRes.ok) {
        const meta = await metaRes.json();
        if (meta.last_updated) {
          const d = new Date(meta.last_updated);
          lastUpdatedEl.textContent = `Update: ${d.toLocaleDateString('id-ID',{day:'numeric',month:'short',year:'numeric'})}`;
        }
      }
    } catch (e) { console.warn('Load failed:', e); }

    // Populate provider filter
    const providers = [...new Set(allPromos.map(p => p.source))].sort();
    providers.forEach(prov => {
      const opt = document.createElement('option');
      opt.value = prov; opt.textContent = prov;
      providerSelect.appendChild(opt);
    });

    // Hero stats
    heroStats.textContent = `🔥 ${allPromos.length} promo aktif hari ini`;

    // Hide skeleton, show grid
    skeletonGrid.style.display = 'none';
    grid.style.display = '';
    render();
  }

  // ─── Render ───────────────────────────────────────────────────────────────────
  function render() {
    let filtered = allPromos;

    // Category
    if (activeCategory !== 'semua') filtered = filtered.filter(p => p.category === activeCategory);

    // Expired filter
    filtered = filtered.filter(p => {
      if (!p.valid_until) return true;
      try { const d = parseIndonesianDate(p.valid_until); return !d || d >= new Date().setHours(0,0,0,0); }
      catch { return true; }
    });

    // Provider filter
    if (providerFilter) filtered = filtered.filter(p => p.source === providerFilter);

    // Search
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(p =>
        (p.text||'').toLowerCase().includes(q) ||
        (p.source||'').toLowerCase().includes(q) ||
        (p.code||'').toLowerCase().includes(q)
      );
    }

    // Sort
    if (sortMode === 'diskon') {
      filtered.sort((a,b) => {
        const da = parseInt((a.discount||'0').replace(/\D/g,'')) || 0;
        const db = parseInt((b.discount||'0').replace(/\D/g,'')) || 0;
        return db - da;
      });
    } else {
      filtered.sort((a,b) => (b.scraped_at||'').localeCompare(a.scraped_at||''));
    }

    countEl.textContent = `${filtered.length} promo ditemukan`;

    if (!filtered.length) { grid.innerHTML = ''; emptyEl.style.display = 'block'; return; }
    emptyEl.style.display = 'none';

    grid.innerHTML = filtered.map(p => {
      const tags = [];
      if (p.discount) tags.push(`<span class="tag tag-discount">${p.discount}</span>`);
      if (p.code) tags.push(`<span class="tag tag-code" onclick="copyCode('${p.code}',this)" title="Klik untuk copy">📋 ${p.code}</span>`);
      if (p.valid_until) tags.push(`<span class="tag tag-valid">s/d ${p.valid_until}</span>`);

      const isBookmarked = bookmarks.includes(p.id);
      const timeAgo = p.scraped_at ? getTimeAgo(new Date(p.scraped_at)) : '';
      const catLabel = catLabels[p.category] || p.category;

      return `
        <div class="promo-card">
          <div class="card-header">
            <span class="source">${p.source || 'Unknown'}</span>
            <span class="category-badge">${catLabel}</span>
          </div>
          <div class="card-text">${escapeHtml(p.text || '')}</div>
          ${tags.length ? `<div class="card-tags">${tags.join('')}</div>` : ''}
          <div class="card-footer">
            <span class="time">${timeAgo}</span>
            <div class="card-actions">
              <button class="action-btn" onclick="toggleBookmark('${p.id}')" title="${isBookmarked?'Hapus bookmark':'Bookmark'}">
                ${isBookmarked ? '❤️' : '🤍'}
              </button>
              <button class="action-btn" onclick="shareWA(\`${escapeHtml(p.text||'').slice(0,100)}\`,\`${p.source_url||''}\`)" title="Share WhatsApp">
                💬
              </button>
              ${p.source_url && p.source_url !== '#' ? `<a href="${p.source_url}" target="_blank" rel="noopener" class="source-link">Lihat →</a>` : ''}
            </div>
          </div>
        </div>`;
    }).join('');
  }

  // ─── Helpers ──────────────────────────────────────────────────────────────────
  function escapeHtml(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/`/g,'&#96;'); }

  function getTimeAgo(date) {
    const diff = (Date.now() - date.getTime()) / 1000;
    if (diff < 3600) return `${Math.floor(diff/60)} menit lalu`;
    if (diff < 86400) return `${Math.floor(diff/3600)} jam lalu`;
    if (diff < 604800) return `${Math.floor(diff/86400)} hari lalu`;
    return date.toLocaleDateString('id-ID',{day:'numeric',month:'short'});
  }

  // ─── Global functions ─────────────────────────────────────────────────────────
  window.copyCode = function(code, el) {
    navigator.clipboard.writeText(code);
    const orig = el.innerHTML;
    el.innerHTML = '✅ Copied!';
    el.classList.add('copied');
    setTimeout(() => { el.innerHTML = orig; el.classList.remove('copied'); }, 1500);
  };

  window.toggleBookmark = function(id) {
    const idx = bookmarks.indexOf(id);
    if (idx > -1) bookmarks.splice(idx, 1);
    else bookmarks.push(id);
    localStorage.setItem('pt-bookmarks', JSON.stringify(bookmarks));
    render();
  };

  window.shareWA = function(text, url) {
    const msg = `Promo: ${text}... ${url}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(msg)}`, '_blank');
  };

  // ─── Events ───────────────────────────────────────────────────────────────────
  document.getElementById('catPills').addEventListener('click', e => {
    const btn = e.target.closest('.pill');
    if (!btn) return;
    document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    activeCategory = btn.dataset.cat;
    render();
  });

  searchInput.addEventListener('input', e => { searchQuery = e.target.value.trim(); render(); });
  sortSelect.addEventListener('change', e => { sortMode = e.target.value; render(); });
  providerSelect.addEventListener('change', e => { providerFilter = e.target.value; render(); });

  // Scroll to top
  window.addEventListener('scroll', () => {
    scrollTopBtn.classList.toggle('visible', window.scrollY > 400);
  });
  scrollTopBtn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

  // ─── Init ─────────────────────────────────────────────────────────────────────
  loadData();

  // Register service worker for PWA
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }
})();
