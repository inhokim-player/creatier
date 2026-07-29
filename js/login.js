(function () {
  'use strict';

  document.getElementById('login-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const errEl = document.getElementById('login-error');
    errEl?.classList.add('hidden');
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: document.getElementById('login-email').value.trim().toLowerCase(),
        password: document.getElementById('login-password').value,
      }),
    });
    const data = await res.json();
    if (!data.ok) {
      errEl.textContent = data.message || '이메일 또는 비밀번호가 맞지 않습니다.';
      errEl.classList.remove('hidden');
      return;
    }
    CreatierAuth.setSessionToken(data.token);
    CreatierAuth.purgeLegacyTokens();
    const next = CreatierAuth.safeRedirectPath(
      new URLSearchParams(window.location.search).get('next')
    );
    window.location.replace(next);
  });
})();
