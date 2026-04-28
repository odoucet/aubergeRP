/**
 * Admin authentication module for aubergeRP.
 * Handles login, logout, and token storage.
 */

const ADMIN_TOKEN_KEY = 'auberge_admin_token';
const ADMIN_LOGIN_ENDPOINT = '/api/admin/login';
const ADMIN_LOGOUT_ENDPOINT = '/api/admin/logout';

/**
 * Get the stored admin token from localStorage.
 */
export function getAdminToken() {
  return localStorage.getItem(ADMIN_TOKEN_KEY) || '';
}

/**
 * Store the admin token in localStorage.
 */
export function setAdminToken(token) {
  if (token) {
    localStorage.setItem(ADMIN_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
  }
}

/**
 * Clear the admin token from localStorage.
 */
export function clearAdminToken() {
  localStorage.removeItem(ADMIN_TOKEN_KEY);
}

/**
 * Check if the user is currently authenticated.
 */
export function isAdminAuthenticated() {
  return !!getAdminToken();
}

/**
 * Attempt to login with the given password.
 * Returns the token on success, or throws an error.
 */
export async function adminLogin(password) {
  const response = await fetch(ADMIN_LOGIN_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ password }),
  });

  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail || 'Login failed');
  }

  const data = await response.json();
  const token = data.token;
  setAdminToken(token);
  return token;
}

/**
 * Logout and clear the token.
 */
export async function adminLogout() {
  const token = getAdminToken();
  if (!token) return;

  try {
    await fetch(ADMIN_LOGOUT_ENDPOINT, {
      method: 'POST',
      headers: {
        'X-Admin-Token': token,
      },
    });
  } catch (_) {
    // Ignore errors on logout
  }

  clearAdminToken();
}

/**
 * Make an authenticated API call with the admin token.
 * Automatically includes the X-Admin-Token header.
 */
export async function adminFetch(url, options = {}) {
  const token = getAdminToken();
  if (!token) {
    clearAdminToken();
    renderLoginModal();
    throw new Error('Not authenticated');
  }

  const headers = new Headers(options.headers || {});
  headers.set('X-Admin-Token', token);

  const res = await fetch(url, { ...options, headers });

  if (res.status === 401) {
    clearAdminToken();
    renderLoginModal();
    throw new Error('Session expirée, veuillez vous reconnecter.');
  }

  return res;
}

/**
 * Render the login modal.
 */
function renderLoginModal() {
  const modal = document.createElement('div');
  modal.id = 'admin-login-modal';
  modal.className = 'modal modal-active';
  modal.innerHTML = `
    <div class="modal-overlay"></div>
    <div class="modal-content">
      <h2>Admin Authentication</h2>
      <p>Enter the admin password to access the admin panel.</p>
      <form id="admin-login-form">
        <div class="form-group">
          <label for="admin-password">Password:</label>
          <input
            type="password"
            id="admin-password"
            name="password"
            placeholder="Enter admin password"
            required
            autofocus
          >
        </div>
        <div class="form-error" id="admin-login-error" style="display:none;"></div>
        <div class="form-group form-actions">
          <button type="submit" class="btn btn-primary">Login</button>
        </div>
      </form>
    </div>
  `;

  document.body.appendChild(modal);

  const form = modal.querySelector('#admin-login-form');
  const errorDiv = modal.querySelector('#admin-login-error');
  const submitBtn = form.querySelector('button[type="submit"]');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorDiv.style.display = 'none';
    submitBtn.disabled = true;
    submitBtn.textContent = 'Logging in…';

    try {
      const password = form.querySelector('#admin-password').value;
      await adminLogin(password);
      modal.remove();
      // Reload to trigger auth guards
      window.location.reload();
    } catch (error) {
      errorDiv.textContent = error.message;
      errorDiv.style.display = 'block';
      submitBtn.disabled = false;
      submitBtn.textContent = 'Login';
    }
  });

  return modal;
}

/**
 * Add a logout button to the admin header.
 */
function addLogoutButton() {
  const header = document.querySelector('#header');
  if (!header) return;

  // Check if logout button already exists
  if (header.querySelector('#admin-logout-btn')) return;

  const logoutBtn = document.createElement('button');
  logoutBtn.id = 'admin-logout-btn';
  logoutBtn.className = 'btn btn-small';
  logoutBtn.textContent = 'Logout';
  logoutBtn.style.marginLeft = 'auto';

  logoutBtn.addEventListener('click', async () => {
    await adminLogout();
    window.location.href = '/admin/';
  });

  header.appendChild(logoutBtn);
}

/**
 * Initialize admin authentication.
 * If not authenticated, show login modal.
 * If authenticated, add logout button.
 */
export async function initAdminAuth() {
  if (!isAdminAuthenticated()) {
    renderLoginModal();
    return false;
  }
  addLogoutButton();
  return true;
}
