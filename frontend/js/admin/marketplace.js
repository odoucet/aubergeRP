/**
 * admin/marketplace.js — Character card marketplace browser for the Admin UI.
 *
 * Exports initMarketplace({ showToast }) → { refresh }
 */

// ── API helpers ──────────────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

// ── DOM refs ─────────────────────────────────────────────────────────────────

const searchInput  = document.getElementById('marketplace-search');
const searchBtn    = document.getElementById('marketplace-search-btn');
const resultsEl    = document.getElementById('marketplace-results');

// ── State ─────────────────────────────────────────────────────────────────────

let showToastFn = () => {};

// ── Init ──────────────────────────────────────────────────────────────────────

export function initMarketplace({ showToast }) {
  if (!searchInput || !searchBtn || !resultsEl) {
    console.error('Marketplace: required DOM elements not found.');
    return { refresh: () => {} };
  }
  showToastFn = showToast;
  searchBtn.addEventListener('click', handleSearch);
  searchInput.addEventListener('keydown', e => { if (e.key === 'Enter') handleSearch(); });
  return { refresh };
}

// ── Load & render ─────────────────────────────────────────────────────────────

async function refresh() {
  await handleSearch();
}

async function handleSearch() {
  const q = (searchInput ? searchInput.value : '').trim();
  resultsEl.innerHTML = '<div class="loading-row">Searching…</div>';
  try {
    const data = await apiFetch(`/api/marketplace/search?q=${encodeURIComponent(q)}`);
    renderResults(data.cards);
  } catch (err) {
    resultsEl.innerHTML = `<div class="error-banner">Marketplace unavailable: ${escHtml(err.message)}</div>`;
  }
}

function renderResults(cards) {
  if (!cards.length) {
    resultsEl.innerHTML = '<div class="loading-row">No cards found.</div>';
    return;
  }
  resultsEl.innerHTML = cards.map(renderCard).join('');
  resultsEl.querySelectorAll('[data-action="import"]').forEach(btn => {
    btn.addEventListener('click', () => handleImport(btn.dataset.url, btn.dataset.name));
  });
}

function renderCard(card) {
  const preview = card.preview_url
    ? `<img class="marketplace-preview" src="${escHtml(card.preview_url)}" alt="${escHtml(card.name)} preview" loading="lazy">`
    : `<div class="marketplace-no-preview" aria-hidden="true">🧝</div>`;
  const tags = card.tags.length ? `<div class="char-card-tags">${escHtml(card.tags.join(', '))}</div>` : '';
  return `
    <div class="char-card marketplace-card">
      ${preview}
      <div class="char-card-info">
        <div class="char-card-name">${escHtml(card.name)}</div>
        ${card.description ? `<div class="char-card-desc">${escHtml(card.description)}</div>` : ''}
        ${card.creator ? `<div class="char-card-tags">By: ${escHtml(card.creator)}</div>` : ''}
        ${tags}
      </div>
      <div class="char-card-actions">
        <button class="btn btn-primary btn-sm" data-action="import" data-url="${escHtml(card.download_url)}" data-name="${escHtml(card.name)}">Import</button>
      </div>
    </div>
  `;
}

async function handleImport(downloadUrl, name) {
  try {
    // Fetch the card JSON from the marketplace
    const res = await fetch(downloadUrl);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    const file = new File([blob], `${name}.json`, { type: 'application/json' });

    const fd = new FormData();
    fd.append('file', file);
    await apiFetch('/api/characters/import', { method: 'POST', body: fd });
    showToastFn(`'${name}' imported successfully.`, false);
  } catch (err) {
    showToastFn(`Import failed: ${err.message}`, true);
  }
}

// ── Util ──────────────────────────────────────────────────────────────────────

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
