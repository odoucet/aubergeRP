/**
 * gui-customization.js — Applies admin-configured CSS and HTML injections.
 *
 * Fetches GET /api/config/gui on load and applies:
 *   - custom_css         → injected as a <style> tag in <head>
 *   - custom_header_html → inserted at the end of the <header> element
 *   - custom_footer_html → inserted before the end of the <footer> element
 *
 * Security note: The header/footer HTML is intentionally rendered via innerHTML
 * because the feature is designed to allow arbitrary HTML injection by the
 * server administrator (accessed only via the Admin UI).  End-users cannot set
 * these values through any API endpoint.  Site operators should restrict access
 * to the Admin UI appropriately.
 */

export async function applyGuiCustomization() {
  let cfg;
  try {
    const res = await fetch('/api/config/gui');
    if (!res.ok) return;
    cfg = await res.json();
  } catch (_) {
    return; // silently ignore — customization is optional
  }

  if (cfg.custom_css) {
    const style = document.createElement('style');
    style.id = 'auberge-custom-css';
    style.textContent = cfg.custom_css;
    document.head.appendChild(style);
  }

  if (cfg.custom_header_html) {
    const header = document.querySelector('header');
    if (header) {
      const div = document.createElement('div');
      div.className = 'custom-header-inject';
      // Admin-controlled HTML injection (see security note in file header)
      div.innerHTML = cfg.custom_header_html; // eslint-disable-line no-unsanitized/property
      header.appendChild(div);
    }
  }

  if (cfg.custom_footer_html) {
    const footer = document.querySelector('footer');
    if (footer) {
      const div = document.createElement('div');
      div.className = 'custom-footer-inject';
      // Admin-controlled HTML injection (see security note in file header)
      div.innerHTML = cfg.custom_footer_html; // eslint-disable-line no-unsanitized/property
      footer.appendChild(div);
    }
  }
}
