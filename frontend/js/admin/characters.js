/**
 * admin/characters.js — Character management for the Admin UI.
 *
 * Exports initCharacters({ showToast, showConfirm }) → { refresh }
 */

import { adminFetch } from '/js/admin/auth.js';

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

const api = {
  listCharacters:   ()          => apiFetch('/api/characters/'),
  getCharacter:     (id)        => apiFetch(`/api/characters/${id}`),
  createCharacter:  (body)      => apiFetch('/api/characters/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  updateCharacter:  (id, body)  => apiFetch(`/api/characters/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  deleteCharacter:  (id)        => apiFetch(`/api/characters/${id}`, { method: 'DELETE' }),
  duplicateCharacter:(id)       => apiFetch(`/api/characters/${id}/duplicate`, { method: 'POST' }),
  uploadAvatar:     (id, file)  => {
    const fd = new FormData();
    fd.append('file', file);
    return apiFetch(`/api/characters/${id}/avatar`, { method: 'POST', body: fd });
  },
  importCharacter:  (file)      => {
    const fd = new FormData();
    fd.append('file', file);
    return apiFetch('/api/characters/import', { method: 'POST', body: fd });
  },
  exportJson:       (id)        => `/api/characters/${id}/export/json`,
  exportPng:        (id)        => `/api/characters/${id}/export/png`,
  avatarUrl:        (id)        => `/api/characters/${id}/avatar`,
};

// ── DOM refs ─────────────────────────────────────────────────────────────────

const listEl        = document.getElementById('character-list');
const importBtn     = document.getElementById('import-char-btn');
const newBtn        = document.getElementById('new-char-btn');

// Import dialog
const importDialog  = document.getElementById('import-dialog');
const importClose   = document.getElementById('import-dialog-close');
const importCancel  = document.getElementById('import-dialog-cancel');
const importDropZone= document.getElementById('import-drop-zone');
const importFileInp = document.getElementById('import-file-input');
const importError   = document.getElementById('import-error');

// Char edit dialog
const charDialog    = document.getElementById('char-dialog');
const charDialogTitle = document.getElementById('char-dialog-title');
const charDialogFeedback = document.getElementById('char-dialog-feedback');
const charClose     = document.getElementById('char-dialog-close');
const charCancel    = document.getElementById('char-dialog-cancel');
const charSave      = document.getElementById('char-dialog-save');
const charAvatarImg = document.getElementById('char-edit-avatar');
const charAvatarUploadBtn = document.getElementById('char-avatar-upload-btn');
const charAvatarInput = document.getElementById('char-avatar-input');

// Form fields
const fName         = document.getElementById('char-name');
const fDesc         = document.getElementById('char-description');
const fPersonality  = document.getElementById('char-personality');
const fFirstMes     = document.getElementById('char-first-mes');
const fMesExample   = document.getElementById('char-mes-example');
const fScenario     = document.getElementById('char-scenario');
const fSystemPrompt = document.getElementById('char-system-prompt');
const fTags         = document.getElementById('char-tags');
const fImgPrompt    = document.getElementById('char-img-prompt-prefix');
const fNegPrompt    = document.getElementById('char-neg-prompt');
const fCreator      = document.getElementById('char-creator');
const fCreatorNotes = document.getElementById('char-creator-notes');
const fNameError    = document.getElementById('char-name-error');
const fDescError    = document.getElementById('char-desc-error');

// ── State ────────────────────────────────────────────────────────────────────

let editingId = null;  // null = new, string = existing id
let pendingAvatarFile = null;
let showToastFn   = () => {};
let showConfirmFn = () => Promise.resolve(false);

// ── Init ─────────────────────────────────────────────────────────────────────

export function initCharacters({ showToast, showConfirm }) {
  showToastFn   = showToast;
  showConfirmFn = showConfirm;

  importBtn.addEventListener('click', openImportDialog);
  newBtn.addEventListener('click', () => openEditDialog(null));

  // Import dialog
  importClose.addEventListener('click', closeImportDialog);
  importCancel.addEventListener('click', closeImportDialog);
  importDialog.addEventListener('click', e => { if (e.target === importDialog) closeImportDialog(); });

  importDropZone.addEventListener('click', () => importFileInp.click());
  importDropZone.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') importFileInp.click(); });
  importDropZone.addEventListener('dragover', e => { e.preventDefault(); importDropZone.classList.add('drag-over'); });
  importDropZone.addEventListener('dragleave', () => importDropZone.classList.remove('drag-over'));
  importDropZone.addEventListener('drop', e => {
    e.preventDefault();
    importDropZone.classList.remove('drag-over');
    const file = e.dataTransfer?.files?.[0];
    if (file) handleImportFile(file);
  });
  importFileInp.addEventListener('change', () => {
    const file = importFileInp.files?.[0];
    if (file) handleImportFile(file);
  });

  // Edit dialog
  charClose.addEventListener('click', closeEditDialog);
  charCancel.addEventListener('click', closeEditDialog);
  charDialog.addEventListener('click', e => { if (e.target === charDialog) closeEditDialog(); });
  charSave.addEventListener('click', handleSave);

  // Avatar upload
  charAvatarUploadBtn.addEventListener('click', () => charAvatarInput.click());
  charAvatarInput.addEventListener('change', () => {
    const file = charAvatarInput.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) { showToastFn('Please select an image file.', true); return; }
    if (file.size > 10 * 1024 * 1024) { showToastFn('Image must be ≤ 10 MB.', true); return; }
    pendingAvatarFile = file;
    const reader = new FileReader();
    reader.onload = e => { charAvatarImg.src = e.target.result; };
    reader.readAsDataURL(file);
  });

  refresh();
  return { refresh };
}

// ── Render character list ─────────────────────────────────────────────────────

async function refresh() {
  listEl.innerHTML = '<div class="loading-row">Loading…</div>';
  try {
    const chars = await api.listCharacters();
    renderList(chars);
  } catch (err) {
    listEl.innerHTML = `<div class="error-banner">Cannot load characters: ${err.message}</div>`;
  }
}

function renderList(chars) {
  if (!chars.length) {
    listEl.innerHTML = '<div class="loading-row">No characters yet. Import or create one.</div>';
    return;
  }
  listEl.innerHTML = chars.map(c => renderCharCard(c)).join('');
  listEl.querySelectorAll('[data-action]').forEach(el => {
    el.addEventListener('click', handleCardAction);
  });
  listEl.querySelectorAll('.dropdown-toggle').forEach(btn => {
    btn.addEventListener('click', e => {
      e.stopPropagation();
      const menu = btn.nextElementSibling;
      const isOpen = menu.style.display === 'block';
      closeAllDropdowns();
      menu.style.display = isOpen ? 'none' : 'block';
    });
  });
}

function closeAllDropdowns() {
  listEl.querySelectorAll('.dropdown-menu').forEach(m => { m.style.display = 'none'; });
}

function renderCharCard(c) {
  const avatarSrc = c.has_avatar ? api.avatarUrl(c.id) : '';
  const avatarEl  = avatarSrc
    ? `<img class="char-card-avatar" src="${escHtml(avatarSrc)}" alt="${escHtml(c.name)} avatar" loading="lazy">`
    : `<div class="char-card-avatar" aria-hidden="true" style="display:flex;align-items:center;justify-content:center;font-size:1.6rem;">🧝</div>`;

  const tags = Array.isArray(c.tags) && c.tags.length ? c.tags.join(', ') : '';

  return `
    <div class="char-card" data-id="${c.id}">
      ${avatarEl}
      <div class="char-card-info">
        <div class="char-card-name">${escHtml(c.name)}</div>
        ${c.description ? `<div class="char-card-desc">${escHtml(c.description)}</div>` : ''}
        ${tags ? `<div class="char-card-tags">Tags: ${escHtml(tags)}</div>` : ''}
      </div>
      <div class="char-card-actions">
        <button class="btn btn-secondary btn-sm" data-action="edit" data-id="${c.id}">Edit</button>
        <div class="dropdown-wrap">
          <button class="btn-icon dropdown-toggle" title="More actions" aria-label="More actions for ${escHtml(c.name)}">⋮</button>
          <div class="dropdown-menu" style="display:none">
            <button data-action="duplicate" data-id="${c.id}">Duplicate</button>
            <button data-action="export-json" data-id="${c.id}">Export as JSON</button>
            <button data-action="export-png" data-id="${c.id}">Export as PNG</button>
            <button data-action="delete" data-id="${c.id}" class="danger">Delete</button>
          </div>
        </div>
      </div>
    </div>
  `;
}

async function handleCardAction(e) {
  const btn    = e.currentTarget;
  const action = btn.dataset.action;
  const id     = btn.dataset.id;
  closeAllDropdowns();

  if (action === 'edit') {
    await openEditDialog(id);
  } else if (action === 'duplicate') {
    try {
      await api.duplicateCharacter(id);
      showToastFn('Character duplicated.', false);
      await refresh();
    } catch (err) {
      showToastFn(`Duplicate failed: ${err.message}`, true);
    }
  } else if (action === 'export-json') {
    downloadUrl(api.exportJson(id));
  } else if (action === 'export-png') {
    downloadUrl(api.exportPng(id));
  } else if (action === 'delete') {
    const card = listEl.querySelector(`.char-card[data-id="${id}"]`);
    const name = card?.querySelector('.char-card-name')?.textContent?.trim() || 'this character';
    const ok = await showConfirmFn(`Are you sure you want to delete ${name}? This cannot be undone.`);
    if (!ok) return;
    try {
      await api.deleteCharacter(id);
      showToastFn('Character deleted.', false);
      await refresh();
    } catch (err) {
      showToastFn(`Delete failed: ${err.message}`, true);
    }
  }
}

function downloadUrl(url) {
  const a = document.createElement('a');
  a.href = url;
  a.download = '';
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// ── Import dialog ─────────────────────────────────────────────────────────────

function openImportDialog() {
  importError.textContent = '';
  importFileInp.value = '';
  importDialog.style.display = 'flex';
}

function closeImportDialog() {
  importDialog.style.display = 'none';
}

async function handleImportFile(file) {
  importError.textContent = '';
  importFileInp.value = '';
  try {
    await api.importCharacter(file);
    showToastFn('Character imported successfully.', false);
    closeImportDialog();
    await refresh();
  } catch (err) {
    importError.textContent = err.message;
  }
}

// ── Edit dialog ───────────────────────────────────────────────────────────────

async function openEditDialog(id) {
  editingId = id;
  pendingAvatarFile = null;
  fNameError.textContent = '';
  fDescError.textContent = '';
  charDialogFeedback.innerHTML = '';
  charAvatarInput.value = '';

  if (id) {
    charDialogTitle.textContent = 'Edit Character';
    try {
      const char = await api.getCharacter(id);
      const d = char.data || char;
      fName.value         = d.name || '';
      fDesc.value         = d.description || '';
      fPersonality.value  = d.personality || '';
      fFirstMes.value     = d.first_mes || '';
      fMesExample.value   = d.mes_example || '';
      fScenario.value     = d.scenario || '';
      fSystemPrompt.value = d.system_prompt || '';
      fTags.value         = Array.isArray(d.tags) ? d.tags.join(', ') : (d.tags || '');
      fImgPrompt.value    = d.extensions?.auberge?.image_prompt_prefix || '';
      fNegPrompt.value    = d.extensions?.auberge?.negative_prompt || '';
      fCreator.value      = d.creator || '';
      fCreatorNotes.value = d.creator_notes || '';

      if (char.has_avatar || char.avatar_url) {
        charAvatarImg.src = api.avatarUrl(id);
        charAvatarImg.style.display = '';
      } else {
        charAvatarImg.src = '';
        charAvatarImg.style.display = 'none';
      }
    } catch (err) {
      showToastFn(`Failed to load character: ${err.message}`, true);
      return;
    }
  } else {
    charDialogTitle.textContent = 'New Character';
    [fName, fDesc, fPersonality, fFirstMes, fMesExample, fScenario,
     fSystemPrompt, fTags, fImgPrompt, fNegPrompt, fCreator, fCreatorNotes].forEach(el => { el.value = ''; });
    charAvatarImg.src = '';
    charAvatarImg.style.display = 'none';
  }

  charDialog.style.display = 'flex';
  fName.focus();
}

function closeEditDialog() {
  charDialog.style.display = 'none';
  editingId = null;
  pendingAvatarFile = null;
}

async function handleSave() {
  fNameError.textContent = '';
  fDescError.textContent = '';
  charDialogFeedback.innerHTML = '';

  const name = fName.value.trim();
  const desc = fDesc.value.trim();
  if (!name) { fNameError.textContent = 'Name is required.'; fName.focus(); return; }
  if (!desc) { fDescError.textContent = 'Description is required.'; fDesc.focus(); return; }

  const tags = fTags.value.split(',').map(t => t.trim()).filter(Boolean);

  const body = {
    name,
    description: desc,
    personality:  fPersonality.value.trim(),
    first_mes:    fFirstMes.value.trim(),
    mes_example:  fMesExample.value.trim(),
    scenario:     fScenario.value.trim(),
    system_prompt: fSystemPrompt.value.trim(),
    tags,
    creator:      fCreator.value.trim(),
    creator_notes: fCreatorNotes.value.trim(),
    extensions: {
      auberge: {
        image_prompt_prefix: fImgPrompt.value.trim(),
        negative_prompt:     fNegPrompt.value.trim(),
      }
    }
  };

  charSave.disabled = true;
  charSave.textContent = 'Saving…';

  try {
    let savedChar;
    if (editingId) {
      savedChar = await api.updateCharacter(editingId, body);
    } else {
      savedChar = await api.createCharacter(body);
    }

    // Upload avatar if one was selected
    if (pendingAvatarFile && savedChar?.id) {
      try {
        await api.uploadAvatar(savedChar.id, pendingAvatarFile);
      } catch (avatarErr) {
        showToastFn(`Character saved but avatar upload failed: ${avatarErr.message}`, true);
        closeEditDialog();
        await refresh();
        return;
      }
    }

    showToastFn(editingId ? 'Character saved.' : 'Character created.', false);
    closeEditDialog();
    await refresh();
  } catch (err) {
    charDialogFeedback.innerHTML = `<div class="error-banner">${escHtml(err.message)}</div>`;
  } finally {
    charSave.disabled = false;
    charSave.textContent = 'Save';
  }
}

// ── Util ─────────────────────────────────────────────────────────────────────

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
