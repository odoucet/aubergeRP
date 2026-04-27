/**
 * admin/medias.js — Media library management for the Admin UI.
 *
 * Exports initMedias({ showToast, showConfirm }) -> { refresh }
 */

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
  if (res.status === 204) return null;
  return res.json();
}

const api = {
  listMedias: () => apiFetch('/api/media/'),
  deleteMedia: (id) => apiFetch(`/api/media/${id}`, { method: 'DELETE' }),
};

const listEl = document.getElementById('medias-list');
const feedbackEl = document.getElementById('medias-feedback');
const refreshBtn = document.getElementById('refresh-medias-btn');

let showToastFn = () => {};
let showConfirmFn = () => Promise.resolve(false);

export function initMedias({ showToast, showConfirm }) {
  showToastFn = showToast;
  showConfirmFn = showConfirm;

  refreshBtn?.addEventListener('click', refresh);
  listEl?.addEventListener('click', handleListClick);

  return { refresh };
}

async function refresh() {
  if (!listEl) return;
  if (feedbackEl) feedbackEl.innerHTML = '';

  listEl.innerHTML = '<div class="loading-row">Loading…</div>';
  try {
    const medias = await api.listMedias();
    renderList(Array.isArray(medias) ? medias : []);
  } catch (err) {
    listEl.innerHTML = `<div class="error-banner">Cannot load medias: ${escHtml(err.message)}</div>`;
  }
}

function renderList(medias) {
  if (!listEl) return;
  if (!medias.length) {
    listEl.innerHTML = '<div class="loading-row">No generated media yet.</div>';
    return;
  }

  listEl.innerHTML = medias.map(renderCard).join('');
}

function renderCard(media) {
  const mediaType = normalizeMediaType(media.media_type, media.media_url);
  const player = renderPlayer(mediaType, media.media_url);
  const promptHtml = media.prompt
    ? `<div class="media-prompt"><div class="media-prompt-label">Prompt</div><pre>${escHtml(media.prompt)}</pre></div>`
    : '<div class="media-prompt-empty">No prompt recorded</div>';

  return `
    <article class="media-card" data-media-id="${escHtml(media.id)}">
      <div class="media-preview-wrap">${player}</div>
      <div class="media-meta">
        <div class="media-row media-row-top">
          <span class="media-type-badge">${escHtml(mediaType)}</span>
          <button class="btn btn-danger btn-sm" data-action="delete-media" data-media-id="${escHtml(media.id)}">Delete</button>
        </div>
        <div class="media-row"><strong>Created:</strong> ${escHtml(formatDateTime(media.created_at))}</div>
        <div class="media-row"><strong>Conversation:</strong> ${escHtml(media.conversation_id || '-')}</div>
        <div class="media-row"><strong>Message:</strong> ${escHtml(media.message_id || '-')}</div>
        <div class="media-row"><strong>URL:</strong> <a href="${escAttr(media.media_url)}" target="_blank" rel="noopener">${escHtml(media.media_url)}</a></div>
        ${promptHtml}
      </div>
    </article>
  `;
}

function renderPlayer(mediaType, mediaUrl) {
  const safeUrl = escAttr(mediaUrl);
  if (mediaType === 'image') {
    return `<img class="media-thumb" loading="lazy" src="${safeUrl}" alt="Generated image">`;
  }
  if (mediaType === 'video') {
    return `<video class="media-player" controls preload="metadata" src="${safeUrl}"></video>`;
  }
  if (mediaType === 'audio') {
    return `<audio class="media-player" controls preload="metadata" src="${safeUrl}"></audio>`;
  }
  return `<a class="btn btn-secondary" href="${safeUrl}" target="_blank" rel="noopener">Open media</a>`;
}

function normalizeMediaType(mediaType, mediaUrl) {
  const t = String(mediaType || '').toLowerCase();
  if (t === 'image' || t === 'video' || t === 'audio') {
    return t;
  }
  return inferTypeFromUrl(mediaUrl);
}

function inferTypeFromUrl(url) {
  const lower = String(url || '').toLowerCase();
  if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg') || lower.endsWith('.gif') || lower.endsWith('.webp')) {
    return 'image';
  }
  if (lower.endsWith('.mp4') || lower.endsWith('.webm') || lower.endsWith('.mov') || lower.endsWith('.mkv')) {
    return 'video';
  }
  if (lower.endsWith('.mp3') || lower.endsWith('.wav') || lower.endsWith('.m4a') || lower.endsWith('.flac') || lower.endsWith('.ogg')) {
    return 'audio';
  }
  return 'image';
}

async function handleListClick(event) {
  const target = event.target;
  if (!(target instanceof Element)) return;

  const action = target.getAttribute('data-action');
  if (action !== 'delete-media') return;

  const mediaId = target.getAttribute('data-media-id');
  if (!mediaId) return;

  const ok = await showConfirmFn('Delete this media and its associated file from disk?');
  if (!ok) return;

  target.setAttribute('disabled', 'true');
  try {
    await api.deleteMedia(mediaId);
    showToastFn('Media deleted.', false);
    await refresh();
  } catch (err) {
    showToastFn(`Delete failed: ${err.message}`, true);
  } finally {
    target.removeAttribute('disabled');
  }
}

function formatDateTime(value) {
  if (!value) return '-';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString();
}

function escHtml(input) {
  return String(input)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function escAttr(input) {
  return escHtml(input).replace(/`/g, '&#96;');
}
