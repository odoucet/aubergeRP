/**
 * admin/connectors.js — Connector management for the Admin UI.
 *
 * Exports initConnectors({ showToast, showConfirm }) → { refresh }
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
  if (res.status === 204) return null;
  return res.json();
}

const api = {
  listConnectors:     ()       => apiFetch('/api/connectors/'),
  listBackends:       ()       => apiFetch('/api/connectors/backends'),
  createConnector:    (body)   => apiFetch('/api/connectors/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  updateConnector:    (id, b)  => apiFetch(`/api/connectors/${id}`, { method: 'PUT',  headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) }),
  deleteConnector:    (id)     => apiFetch(`/api/connectors/${id}`, { method: 'DELETE' }),
  testConnector:      (id)     => apiFetch(`/api/connectors/${id}/test`, { method: 'POST' }),
  activateConnector:  (id)     => apiFetch(`/api/connectors/${id}/activate`, { method: 'POST' }),
};

// ── DOM refs ─────────────────────────────────────────────────────────────────

const listEl      = document.getElementById('connector-list');
const addBtn      = document.getElementById('add-connector-btn');

// Dialog elements
const dialog      = document.getElementById('connector-dialog');
const dialogTitle = document.getElementById('connector-dialog-title');
const dialogFeedback = document.getElementById('connector-dialog-feedback');
const closeBtn    = document.getElementById('connector-dialog-close');
const cancelBtn   = document.getElementById('connector-dialog-cancel');
const testBtn     = document.getElementById('connector-dialog-test');
const saveBtn     = document.getElementById('connector-dialog-save');
const nameInput   = document.getElementById('conn-name');
const typeSelect  = document.getElementById('conn-type');
const backendSelect = document.getElementById('conn-backend');
const configFields  = document.getElementById('conn-config-fields');
const clearKeyRow   = document.getElementById('conn-clear-key-row');
const clearKeyChk   = document.getElementById('conn-clear-key');
const nameError     = document.getElementById('conn-name-error');

// ── State ────────────────────────────────────────────────────────────────────

let backends = [];         // from GET /api/connectors/backends
let editingId = null;      // null = new, string = existing id
let existingApiKeySet = false;
let showToastFn = () => {};
let showConfirmFn = () => Promise.resolve(false);

// ── Init ─────────────────────────────────────────────────────────────────────

export function initConnectors({ showToast, showConfirm }) {
  showToastFn   = showToast;
  showConfirmFn = showConfirm;

  addBtn.addEventListener('click', () => openDialog(null));
  closeBtn.addEventListener('click', closeDialog);
  cancelBtn.addEventListener('click', closeDialog);
  saveBtn.addEventListener('click', handleSave);
  testBtn.addEventListener('click', handleTest);
  typeSelect.addEventListener('change', onTypeChange);
  backendSelect.addEventListener('change', onBackendChange);

  // Close on backdrop click
  dialog.addEventListener('click', e => { if (e.target === dialog) closeDialog(); });

  loadBackends();
  refresh();

  return { refresh };
}

// ── Load backends schema ──────────────────────────────────────────────────────

async function loadBackends() {
  try {
    backends = await api.listBackends();
    updateBackendOptions();
  } catch (_) {
    // If backends endpoint not available, use a default schema
    backends = [{
      id: 'openai_api',
      name: 'OpenAI-Compatible API',
      supported_types: ['text', 'image', 'video', 'audio'],
      config_schema: {
        base_url:    { type: 'string', required: true },
        api_key:     { type: 'string', required: false },
        model:       { type: 'string', required: true },
        max_tokens:  { type: 'number', required: false },
        temperature: { type: 'number', required: false },
        timeout:     { type: 'number', required: false },
      }
    }];
    updateBackendOptions();
  }
}

// ── Render connector list ─────────────────────────────────────────────────────

async function refresh() {
  listEl.innerHTML = '<div class="loading-row">Loading…</div>';
  try {
    const connectors = await api.listConnectors();
    renderList(connectors);
  } catch (err) {
    listEl.innerHTML = `<div class="error-banner">Cannot load connectors: ${err.message}</div>`;
  }
}

const CONNECTOR_TYPES = ['text', 'image', 'video', 'audio'];

function renderList(connectors) {
  const byType = {};
  CONNECTOR_TYPES.forEach(t => { byType[t] = []; });
  connectors.forEach(c => {
    if (!byType[c.type]) byType[c.type] = [];
    byType[c.type].push(c);
  });

  const html = CONNECTOR_TYPES.map(type => {
    const group = byType[type] || [];
    const items = group.length === 0
      ? '<div class="conn-empty">(none)</div>'
      : group.map(c => renderConnectorCard(c)).join('');
    return `
      <div class="conn-type-heading">${type} Connectors</div>
      ${items}
    `;
  }).join('');

  listEl.innerHTML = html || '<div class="loading-row">No connectors configured.</div>';

  // Attach event listeners to action buttons
  listEl.querySelectorAll('[data-action]').forEach(el => {
    el.addEventListener('click', handleCardAction);
  });

  // Dropdown toggles
  listEl.querySelectorAll('.dropdown-toggle').forEach(btn => {
    btn.addEventListener('click', e => {
      e.stopPropagation();
      const menu = btn.nextElementSibling;
      const isOpen = menu.style.display === 'block';
      closeAllDropdowns();
      menu.style.display = isOpen ? 'none' : 'block';
    });
  });

  document.addEventListener('click', closeAllDropdowns, { once: false });
}

function closeAllDropdowns() {
  listEl.querySelectorAll('.dropdown-menu').forEach(m => { m.style.display = 'none'; });
}

function renderConnectorCard(c) {
  const star = c.is_active ? '<span class="conn-active-star" title="Active">⭐</span>' : '<span class="conn-active-star"></span>';
  const statusClass = c.connected === true ? 'ok' : c.connected === false ? 'fail' : 'unknown';
  const statusText  = c.connected === true ? '✅ Connected' : c.connected === false ? '❌ Not connected' : '— Not tested';
  const meta = c.config ? [
    c.config.base_url ? `URL: ${c.config.base_url}` : '',
    c.config.model    ? `Model: ${c.config.model}` : '',
  ].filter(Boolean).join(' &nbsp;·&nbsp; ') : '';

  return `
    <div class="conn-card" data-id="${c.id}">
      ${star}
      <div class="conn-info">
        <div class="conn-name">
          ${escHtml(c.name)}
          <span class="conn-backend-badge">${escHtml(c.backend)}</span>
        </div>
        ${meta ? `<div class="conn-meta">${meta}</div>` : ''}
        <div class="conn-status ${statusClass}" id="conn-status-${c.id}">${statusText}</div>
      </div>
      <div class="conn-actions">
        <button class="btn btn-secondary btn-sm" data-action="test" data-id="${c.id}">Test</button>
        <div class="dropdown-wrap">
          <button class="btn-icon dropdown-toggle" title="More actions" aria-label="More actions for ${escHtml(c.name)}">⋮</button>
          <div class="dropdown-menu" style="display:none">
            <button data-action="edit" data-id="${c.id}">Edit</button>
            ${!c.is_active ? `<button data-action="activate" data-id="${c.id}">Activate</button>` : ''}
            <button data-action="delete" data-id="${c.id}" class="danger">Delete</button>
          </div>
        </div>
      </div>
    </div>
  `;
}

async function handleCardAction(e) {
  const btn = e.currentTarget;
  const action = btn.dataset.action;
  const id = btn.dataset.id;
  closeAllDropdowns();

  if (action === 'test') {
    btn.disabled = true;
    btn.textContent = '…';
    try {
      const result = await api.testConnector(id);
      if (result.connected) {
        const detail = result.details ? JSON.stringify(result.details) : '';
        showToastFn(`Connected.${detail ? ' ' + detail : ''}`, false);
      } else {
        showToastFn(result.detail || 'Connection failed.', true);
      }
    } catch (err) {
      showToastFn(`Test failed: ${err.message}`, true);
    } finally {
      await refresh();
    }
  } else if (action === 'edit') {
    await openDialog(id);
  } else if (action === 'activate') {
    try {
      await api.activateConnector(id);
      showToastFn('Connector activated.', false);
      await refresh();
    } catch (err) {
      showToastFn(`Activate failed: ${err.message}`, true);
    }
  } else if (action === 'delete') {
    const card = listEl.querySelector(`.conn-card[data-id="${id}"]`);
    const name = card?.querySelector('.conn-name')?.childNodes[0]?.textContent?.trim() || 'this connector';
    const ok = await showConfirmFn(`Are you sure you want to delete ${name}? This cannot be undone.`);
    if (!ok) return;
    try {
      await api.deleteConnector(id);
      showToastFn('Connector deleted.', false);
      await refresh();
    } catch (err) {
      showToastFn(`Delete failed: ${err.message}`, true);
    }
  }
}

// ── Dialog ────────────────────────────────────────────────────────────────────

async function openDialog(id) {
  editingId = id;
  clearKeyChk.checked = false;
  clearKeyRow.style.display = 'none';
  dialogFeedback.innerHTML = '';
  nameError.textContent = '';
  existingApiKeySet = false;

  if (id) {
    dialogTitle.textContent = 'Edit Connector';
    try {
      const conn = await apiFetch(`/api/connectors/${id}`);
      nameInput.value = conn.name || '';
      typeSelect.value = conn.type || 'text';
      updateBackendOptions();
      backendSelect.value = conn.backend || 'openai_api';
      renderConfigFields(conn.backend, conn.config || {});
      existingApiKeySet = !!(conn.config && conn.config.api_key_set);
      clearKeyRow.style.display = existingApiKeySet ? '' : 'none';
    } catch (err) {
      showToastFn(`Failed to load connector: ${err.message}`, true);
      return;
    }
  } else {
    dialogTitle.textContent = 'Add New Connector';
    nameInput.value = '';
    typeSelect.value = 'text';
    updateBackendOptions();
    renderConfigFields(backendSelect.value, {});
  }

  dialog.style.display = 'flex';
  nameInput.focus();
}

function closeDialog() {
  dialog.style.display = 'none';
  editingId = null;
}

function onTypeChange() {
  updateBackendOptions();
  renderConfigFields(backendSelect.value, {});
}

function onBackendChange() {
  renderConfigFields(backendSelect.value, {});
}

function updateBackendOptions() {
  const selectedType = typeSelect.value;
  const compatible = backends.filter(b =>
    !b.supported_types || b.supported_types.includes(selectedType)
  );
  const prev = backendSelect.value;
  backendSelect.innerHTML = compatible.map(b =>
    `<option value="${escHtml(b.id)}">${escHtml(b.name || b.id)}</option>`
  ).join('');
  if (compatible.find(b => b.id === prev)) backendSelect.value = prev;
}

function renderConfigFields(backendId, existingConfig) {
  const backend = backends.find(b => b.id === backendId);
  if (!backend || !backend.config_schema) {
    // Render a generic set
    configFields.innerHTML = renderField('base_url', 'Base URL', 'string', true, existingConfig.base_url || '')
      + renderField('api_key', 'API Key', 'string', false, '')
      + renderField('model', 'Model', 'string', true, existingConfig.model || '');
    return;
  }
  configFields.innerHTML = Object.entries(backend.config_schema)
    .filter(([key]) => key !== 'api_key_set')
    .map(([key, schema]) => {
      const isApiKey = key === 'api_key';
      let val = isApiKey ? '' : (existingConfig[key] !== undefined ? String(existingConfig[key]) : '');
      let placeholder = isApiKey && existingApiKeySet ? '(set — leave blank to keep)' : '';
      if (schema.type === 'workflow_select') {
        return renderWorkflowSelect(key, schemaLabel(key), val);
      }
      return renderField(key, schemaLabel(key), schema.type || 'string', schema.required || false, val, placeholder, isApiKey ? 'password' : null);
    }).join('');

  // Populate workflow select if present
  if (backend.config_schema.workflow?.type === 'workflow_select') {
    populateWorkflowSelect(existingConfig.workflow || 'default');
  }
}

function schemaLabel(key) {
  const map = {
    base_url: 'Base URL', api_key: 'API Key', model: 'Model',
    max_tokens: 'Max Tokens', temperature: 'Temperature', timeout: 'Timeout (s)',
    workflow: 'Workflow',
  };
  return map[key] || key.replace(/_/g, ' ');
}

function renderField(key, label, type, required, value, placeholder = '', inputType = null) {
  const itype = inputType || (type === 'number' ? 'number' : 'text');
  const req = required ? '<span class="required">*</span>' : '';
  return `
    <div class="field-row">
      <label for="cfg-${key}">${escHtml(label)} ${req}</label>
      <input type="${itype}" id="cfg-${key}" name="${key}" value="${escHtml(String(value))}" placeholder="${escHtml(placeholder)}">
    </div>
  `;
}

function renderWorkflowSelect(key, label, currentValue) {
  return `
    <div class="field-row">
      <label for="cfg-${key}">${escHtml(label)}</label>
      <select id="cfg-${key}" name="${key}">
        <option value="${escHtml(currentValue || 'default')}">${escHtml(currentValue || 'default')}</option>
      </select>
    </div>
  `;
}

async function populateWorkflowSelect(selectedValue) {
  const sel = document.getElementById('cfg-workflow');
  if (!sel) return;
  try {
    const workflows = await apiFetch('/api/connectors/comfyui-workflows');
    sel.innerHTML = workflows.map(w =>
      `<option value="${escHtml(w)}"${w === selectedValue ? ' selected' : ''}>${escHtml(w)}</option>`
    ).join('');
    if (!workflows.includes(selectedValue) && selectedValue) {
      const opt = document.createElement('option');
      opt.value = selectedValue;
      opt.textContent = selectedValue;
      opt.selected = true;
      sel.prepend(opt);
    }
  } catch (_) {
    // Keep the placeholder option if the endpoint is unavailable
  }
}

function collectConfig() {
  const cfg = {};
  configFields.querySelectorAll('input[name], select[name]').forEach(inp => {
    const key = inp.name;
    const val = inp.value.trim();
    if (key === 'api_key') {
      // Include only if user typed something, or if clearKeyChk is checked (empty = clear)
      if (val !== '' || clearKeyChk.checked) {
        cfg[key] = val;
      }
      // else omit → server preserves existing key
    } else {
      cfg[key] = inp.type === 'number' ? (val === '' ? undefined : Number(val)) : val;
    }
  });
  return cfg;
}

async function handleTest() {
  if (!editingId) {
    dialogFeedback.innerHTML = '<div class="error-banner">Save the connector first, then test it.</div>';
    return;
  }
  testBtn.disabled = true;
  testBtn.textContent = '…';
  dialogFeedback.innerHTML = '';
  try {
    const result = await api.testConnector(editingId);
    if (result.connected) {
      const detail = result.details ? ` Available: ${JSON.stringify(result.details)}` : '';
      dialogFeedback.innerHTML = `<div class="success-banner">Connected.${escHtml(detail)}</div>`;
    } else {
      dialogFeedback.innerHTML = `<div class="error-banner">${escHtml(result.detail || 'Connection failed.')}</div>`;
    }
  } catch (err) {
    dialogFeedback.innerHTML = `<div class="error-banner">${escHtml(err.message)}</div>`;
  } finally {
    testBtn.disabled = false;
    testBtn.textContent = 'Test';
  }
}

async function handleSave() {
  nameError.textContent = '';
  dialogFeedback.innerHTML = '';

  const name = nameInput.value.trim();
  if (!name) { nameError.textContent = 'Name is required.'; nameInput.focus(); return; }

  const body = {
    name,
    type: typeSelect.value,
    backend: backendSelect.value,
    config: collectConfig(),
  };

  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving…';

  try {
    if (editingId) {
      await api.updateConnector(editingId, body);
      showToastFn('Connector saved.', false);
    } else {
      await api.createConnector(body);
      showToastFn('Connector created.', false);
    }
    closeDialog();
    await refresh();
  } catch (err) {
    dialogFeedback.innerHTML = `<div class="error-banner">${escHtml(err.message)}</div>`;
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = 'Save';
  }
}

// ── Health badge update ───────────────────────────────────────────────────────

/**
 * Update connector status badges from health data without a full re-render.
 * Called by the 30-second health polling loop in admin/index.html.
 *
 * @param {Object} healthData - response from GET /api/health/
 */
export function applyHealthBadges(healthData) {
  const connectors = healthData?.connectors;
  if (!connectors || typeof connectors !== 'object' || Array.isArray(connectors)) return;
  Object.values(connectors).forEach(c => {
    if (!c || !c.id) return;
    const el = document.getElementById(`conn-status-${c.id}`);
    if (!el) return;
    if (c.connected === true) {
      el.className = 'conn-status ok';
      el.textContent = '✅ Connected';
    } else if (c.connected === false) {
      el.className = 'conn-status fail';
      el.textContent = '❌ Not connected';
    }
  });
}

// ── Util ─────────────────────────────────────────────────────────────────────

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
