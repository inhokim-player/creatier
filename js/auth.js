(function (global) {
  'use strict';

  const ADMIN_SESSION_KEY = 'creatier_admin_sess';
  const LEGACY_KEYS = ['creatier_token', 'accessToken', 'creator_access'];

  function purgeLegacyTokens() {
    LEGACY_KEYS.forEach((k) => {
      try {
        localStorage.removeItem(k);
        sessionStorage.removeItem(k);
      } catch {}
    });
  }

  function getSessionToken() {
    try {
      return sessionStorage.getItem(ADMIN_SESSION_KEY) || '';
    } catch {
      return '';
    }
  }

  function setSessionToken(token) {
    try {
      if (token) sessionStorage.setItem(ADMIN_SESSION_KEY, token);
      else sessionStorage.removeItem(ADMIN_SESSION_KEY);
    } catch {}
  }

  function safeRedirectPath(raw) {
    if (!raw || typeof raw !== 'string') return '/admin';
    const path = raw.trim();
    if (!path.startsWith('/') || path.startsWith('//')) return '/admin';
    if (path.includes('://') || path.includes('\\')) return '/admin';
    if (path.startsWith('/login')) return '/admin';
    return path;
  }

  async function apiFetch(url, options) {
    purgeLegacyTokens();
    const headers = { ...(options?.headers || {}) };
    const token = getSessionToken();
    if (token && !headers.Authorization) {
      headers.Authorization = `Bearer ${token}`;
    }
    return fetch(url, {
      ...(options || {}),
      credentials: 'same-origin',
      headers,
    });
  }

  async function requirePlatform() {
    const res = await apiFetch('/api/auth/me');
    if (res.status === 401) {
      setSessionToken('');
      window.location.href = '/login?next=/admin';
      return null;
    }
    const data = await res.json();
    if (!data.ok || data.user?.role !== 'platform') {
      setSessionToken('');
      window.location.href = '/login?next=/admin';
      return null;
    }
    return data;
  }

  async function logout() {
    try {
      await apiFetch('/api/auth/logout', { method: 'POST' });
    } catch {}
    setSessionToken('');
    purgeLegacyTokens();
    window.location.href = '/login';
  }

  purgeLegacyTokens();
  global.CreatierAuth = {
    apiFetch,
    requirePlatform,
    logout,
    safeRedirectPath,
    purgeLegacyTokens,
    setSessionToken,
  };
})(window);
