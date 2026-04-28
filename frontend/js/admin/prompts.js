import { adminFetch } from '/js/admin/auth.js';

/**
 * admin/prompts.js — Prompt management panel.
 *
 * Exports initPrompts({ showToast }) → { refresh }
 */

// ── API helpers ──────────────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const isWrite = ['POST', 'PUT', 'DELETE', 'PATCH'].includes(method);
  const res = isWrite ? await adminFetch(path, options) : await fetch(path, options);
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

// ── State ─────────────────────────────────────────────────────────────────────

let showToastFn = () => {};
// key → { textarea, saveBtn, resetBtn, dirtyFlag }
const _editors = new Map();

// ── Init ──────────────────────────────────────────────────────────────────────

export function initPrompts({ showToast }) {
  showToastFn = showToast;
  return { refresh };
}

// ── Load & render ─────────────────────────────────────────────────────────────

async function refresh() {
  const feedbackEl = document.getElementById('prompts-feedback');
  const listEl = document.getElementById('prompts-list');
  feedbackEl.innerHTML = '';
  listEl.innerHTML = '<div class="loading-row">Loading…</div>';
  _editors.clear();

  try {
    const prompts = await apiFetch('/api/prompts/');
    renderList(prompts, listEl);
  } catch (err) {
    listEl.innerHTML = '';
    feedbackEl.innerHTML = `<div class="error-banner">Cannot load prompts: ${escHtml(err.message)}</div>`;
  }
}

function renderList(prompts, container) {
  container.innerHTML = '';

  prompts.forEach(prompt => {
    const block = document.createElement('div');
    block.className = 'prompt-block';
    block.dataset.key = prompt.key;

    const header = document.createElement('div');
    header.className = 'prompt-block-header';

    const titleWrap = document.createElement('div');
    titleWrap.className = 'prompt-block-title-wrap';

    const title = document.createElement('strong');
    title.className = 'prompt-block-title';
    title.textContent = prompt.label;

    const badge = document.createElement('span');
    badge.className = 'prompt-badge' + (prompt.is_customized ? ' prompt-badge-custom' : '');
    badge.textContent = prompt.is_customized ? 'customized' : 'default';
    badge.id = `badge-${prompt.key}`;

    titleWrap.appendChild(title);
    titleWrap.appendChild(badge);

    const desc = document.createElement('p');
    desc.className = 'prompt-block-desc';
    desc.textContent = prompt.description;

    const actions = document.createElement('div');
    actions.className = 'prompt-block-actions';

    const saveBtn = document.createElement('button');
    saveBtn.className = 'btn btn-primary btn-sm';
    saveBtn.textContent = 'Save';
    saveBtn.dataset.key = prompt.key;
    saveBtn.addEventListener('click', () => handleSave(prompt.key));

    actions.appendChild(saveBtn);

    if (prompt.has_reset) {
      const resetBtn = document.createElement('button');
      resetBtn.className = 'btn btn-secondary btn-sm';
      resetBtn.textContent = 'Reset to default';
      resetBtn.dataset.key = prompt.key;
      resetBtn.addEventListener('click', () => handleReset(prompt.key));
      actions.appendChild(resetBtn);
      _editors.set(prompt.key, { saveBtn, resetBtn });
    } else {
      _editors.set(prompt.key, { saveBtn, resetBtn: null });
    }

    header.appendChild(titleWrap);
    header.appendChild(actions);

    const textarea = document.createElement('textarea');
    textarea.className = 'prompt-textarea';
    textarea.id = `prompt-ta-${prompt.key}`;
    textarea.rows = computeRows(prompt.content);
    textarea.value = prompt.content;
    textarea.spellcheck = false;
    textarea.addEventListener('input', () => {
      textarea.rows = computeRows(textarea.value);
    });

    const feedbackRow = document.createElement('div');
    feedbackRow.className = 'prompt-feedback';
    feedbackRow.id = `prompt-fb-${prompt.key}`;

    block.appendChild(header);
    block.appendChild(desc);
    block.appendChild(textarea);
    block.appendChild(feedbackRow);

    container.appendChild(block);
  });
}

// ── Save ──────────────────────────────────────────────────────────────────────

async function handleSave(key) {
  const textarea = document.getElementById(`prompt-ta-${key}`);
  const feedbackEl = document.getElementById(`prompt-fb-${key}`);
  const editor = _editors.get(key);
  if (!textarea || !editor) return;

  feedbackEl.textContent = '';
  editor.saveBtn.disabled = true;
  editor.saveBtn.textContent = 'Saving…';

  try {
    await apiFetch(`/api/prompts/${key}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: textarea.value }),
    });
    showToastFn(`Prompt "${key}" saved.`, false);
    updateBadge(key, true);
  } catch (err) {
    feedbackEl.textContent = `Error: ${err.message}`;
    feedbackEl.style.color = 'var(--color-error, red)';
  } finally {
    editor.saveBtn.disabled = false;
    editor.saveBtn.textContent = 'Save';
  }
}

// ── Reset ─────────────────────────────────────────────────────────────────────

async function handleReset(key) {
  const textarea = document.getElementById(`prompt-ta-${key}`);
  const feedbackEl = document.getElementById(`prompt-fb-${key}`);
  const editor = _editors.get(key);
  if (!textarea || !editor || !editor.resetBtn) return;

  feedbackEl.textContent = '';
  editor.resetBtn.disabled = true;
  editor.resetBtn.textContent = 'Resetting…';

  try {
    const result = await apiFetch(`/api/prompts/${key}`, { method: 'DELETE' });
    textarea.value = result.content;
    textarea.rows = computeRows(result.content);
    showToastFn(`Prompt "${key}" reset to default.`, false);
    updateBadge(key, false);
  } catch (err) {
    feedbackEl.textContent = `Error: ${err.message}`;
    feedbackEl.style.color = 'var(--color-error, red)';
  } finally {
    editor.resetBtn.disabled = false;
    editor.resetBtn.textContent = 'Reset to default';
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function updateBadge(key, isCustomized) {
  const badge = document.getElementById(`badge-${key}`);
  if (!badge) return;
  badge.textContent = isCustomized ? 'customized' : 'default';
  badge.className = 'prompt-badge' + (isCustomized ? ' prompt-badge-custom' : '');
}

function computeRows(text) {
  const lines = (text || '').split('\n').length;
  return Math.max(4, Math.min(lines + 1, 30));
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
