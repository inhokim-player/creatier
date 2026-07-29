(function () {
  'use strict';

  const form = document.getElementById('report-form');
  const msg = document.getElementById('report-msg');
  const select = document.getElementById('report-category');

  async function loadCategories() {
    const res = await fetch('/api/report/categories');
    const data = await res.json();
    if (!data.ok) return;
    select.innerHTML = data.categories
      .map((c) => `<option value="${c.id}">${c.label}</option>`)
      .join('');
    const preferred = new URLSearchParams(location.search).get('category');
    if (preferred && [...select.options].some((o) => o.value === preferred)) {
      select.value = preferred;
    }
  }

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    msg.classList.add('hidden');
    const res = await fetch('/api/report/abuse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        category: select.value,
        detail: document.getElementById('report-detail').value,
        contact: document.getElementById('report-contact').value,
      }),
    });
    const data = await res.json();
    msg.classList.remove('hidden');
    msg.textContent = data.message || (data.ok ? '접수되었습니다.' : '접수 실패');
    msg.style.color = data.ok ? '#3182f6' : '#f04452';
    if (data.ok) form.reset();
  });

  loadCategories();
  ContactFooter.render(document.getElementById('contact-footer-slot'));
})();
