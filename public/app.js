// PromoIndo — Client App
(function() {
  let allPromos = [];
  let activeCategory = 'semua';
  let searchQuery = '';

  const grid = document.getElementById('promoGrid');
  const countEl = document.getElementById('promoCount');
  const emptyEl = document.getElementById('emptyState');
  const searchInput = document.getElementById('searchInput');
  const lastUpdatedEl = document.getElementById('lastUpdated');

  // Category labels
  const catLabels = {
    makanan: '🍔 Makanan',
    belanja: '🛍️ Belanja',
    hiburan: '🎬 Hiburan',
    hotel: '🏨 Hotel',
    transport: '🚗 Transport',
    kesehatan: '💊 Kesehatan',
    keuangan: '💳 Keuangan',
    lainnya: '📦 Lainnya',
  };

  // Fetch data
  async function loadData() {
    try {
      const [promosRes, metaRes] = await Promise.all([
        fetch('/data/promos.json'),
        fetch('/data/meta.json'),
      ]);
      if (promosRes.ok) {
        allPromos = await promosRes.json();
      }
      if (metaRes.ok) {
        const meta = await metaRes.json();
        if (meta.last_updated) {
          const d = new Date(meta.last_updated);
          lastUpdatedEl.textContent = `Update: ${d.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' })}`;
        }
      }
    } catch (e) {
      console.warn('Failed to load data:', e);
    }
    render();
  }

  // Render promo cards
  function render() {
    let filtered = allPromos;

    // Filter by category
    if (activeCategory !== 'semua') {
      filtered = filtered.filter(p => p.category === activeCategory);
    }

    // Filter by search
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(p =>
        (p.text || '').toLowerCase().includes(q) ||
        (p.source || '').toLowerCase().includes(q) ||
        (p.code || '').toLowerCase().includes(q)
      );
    }

    // Update count
    countEl.textContent = `${filtered.length} promo ditemukan`;

    // Empty state
    if (filtered.length === 0) {
      grid.innerHTML = '';
      emptyEl.style.display = 'block';
      return;
    }
    emptyEl.style.display = 'none';

    // Render cards
    grid.innerHTML = filtered.map(p => {
      const tags = [];
      if (p.discount) tags.push(`<span class="tag tag-discount">${p.discount}</span>`);
      if (p.code) tags.push(`<span class="tag tag-code">Kode: ${p.code}</span>`);
      if (p.valid_until) tags.push(`<span class="tag tag-valid">s/d ${p.valid_until}</span>`);

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
            ${p.source_url ? `<a href="${p.source_url}" target="_blank" rel="noopener" class="source-link">Lihat →</a>` : ''}
          </div>
        </div>
      `;
    }).join('');
  }

  function escapeHtml(str) {
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function getTimeAgo(date) {
    const diff = (Date.now() - date.getTime()) / 1000;
    if (diff < 3600) return `${Math.floor(diff / 60)} menit lalu`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} jam lalu`;
    if (diff < 604800) return `${Math.floor(diff / 86400)} hari lalu`;
    return date.toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
  }

  // Events
  document.getElementById('catPills').addEventListener('click', e => {
    const btn = e.target.closest('.pill');
    if (!btn) return;
    document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    activeCategory = btn.dataset.cat;
    render();
  });

  searchInput.addEventListener('input', e => {
    searchQuery = e.target.value.trim();
    render();
  });

  // Init
  loadData();
})();
