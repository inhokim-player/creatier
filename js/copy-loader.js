(function (global) {
  'use strict';

  let COPY = {};

  function getPath(obj, path) {
    return path.split('.').reduce((o, k) => (o && o[k] != null ? o[k] : null), obj);
  }

  function t(key, fallback) {
    const v = getPath(COPY, key);
    return v != null && v !== '' ? v : fallback || '';
  }

  function applyCopy(root) {
    document.querySelectorAll('[data-copy]').forEach((el) => {
      const key = el.getAttribute('data-copy');
      const val = t(key, el.textContent);
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
        if (el.hasAttribute('data-copy-placeholder')) {
          el.placeholder = t(el.getAttribute('data-copy-placeholder'), el.placeholder);
        }
      } else if (val.includes('\n')) {
        el.innerHTML = val.split('\n').join('<br />');
      } else {
        el.textContent = val;
      }
    });
    document.querySelectorAll('[data-copy-placeholder]').forEach((el) => {
      if (el.hasAttribute('data-copy')) return;
      el.placeholder = t(el.getAttribute('data-copy-placeholder'), el.placeholder);
    });
    document.querySelectorAll('[data-copy-title]').forEach((el) => {
      el.title = t(el.getAttribute('data-copy-title'), el.title);
    });
    const brand = t('brand.name', '크라잇에이터');
    document.querySelectorAll('[data-brand]').forEach((el) => {
      el.textContent = brand;
    });
  }

  async function initCopy() {
    try {
      const res = await fetch('/api/copy');
      const data = await res.json();
      if (data.ok && data.copy) COPY = data.copy;
    } catch (_) {
      /* fallback: HTML 기본 문구 유지 */
    }
    applyCopy();
    global.CreatierCopy = { t, applyCopy, raw: () => COPY };
    document.dispatchEvent(new CustomEvent('creatier:copy-ready'));
  }

  global.CreatierCopy = { t, applyCopy, raw: () => COPY };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCopy);
  } else {
    initCopy();
  }
})(window);
