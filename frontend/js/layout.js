const STATUS_TYPES = ['text', 'image'];

const STATUS_HELP_TEXT =
  'These are capability categories. A green dot means the active connector for that type ' +
  'is reachable. Red means configured but unavailable. Gray means no connector is set.';

export function initStatusBar() {
  const footer = document.getElementById('statusbar');
  if (!footer) return;
  footer.setAttribute('role', 'contentinfo');
  footer.setAttribute('aria-label', 'Connector status');
  footer.innerHTML =
    STATUS_TYPES.map(t => `
      <div class="status-item" id="status-${t}">
        <div class="status-dot na" aria-hidden="true"></div>
        <span class="status-label">${cap(t)} —</span>
      </div>`).join('') +
    `<div class="status-help" aria-label="About connector statuses">
      <button type="button" class="status-help-btn"
        aria-describedby="status-help-tooltip"
        title="What do these connector types mean?">?</button>
      <span id="status-help-tooltip" class="status-help-tooltip" role="tooltip">
        ${STATUS_HELP_TEXT}
      </span>
    </div>`;
}

export function setStatusItem(type, info) {
  const el = document.getElementById(`status-${type}`);
  if (!el) return;
  const dot = el.querySelector('.status-dot');
  const label = el.querySelector('.status-label');
  if (!info) {
    dot.className = 'status-dot na';
    label.textContent = `${cap(type)} —`;
  } else if (info.connected) {
    dot.className = 'status-dot ok';
    label.textContent = `${cap(type)} ✓`;
  } else {
    dot.className = 'status-dot err';
    label.textContent = `${cap(type)} ✕`;
  }
}

export function initHeaderLogo(options = {}) {
  const logo = document.querySelector('#header .logo');
  if (!logo) return;
  logo.innerHTML =
    `<img class="logo-icon" src="/favicons/favicon-32.svg" alt="" aria-hidden="true">` +
    `<span>aubergeRP</span>` +
    (options.badge ? `<span class="admin-badge">${escHtml(options.badge)}</span>` : '');
}

function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

function escHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
