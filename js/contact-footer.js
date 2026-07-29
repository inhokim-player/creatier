(function () {
  'use strict';

  const DEFAULT_EMAIL = 'a123dlsgh@gmail.com';

  async function fetchContact() {
    try {
      const res = await fetch('/api/contact');
      const data = await res.json();
      if (data.ok) return data;
    } catch {}
    const email = DEFAULT_EMAIL;
    return {
      email,
      mailto: `mailto:${email}?subject=${encodeURIComponent('크라잇에이터 광고·협업 문의')}`,
      reportUrl: '/report?category=ads',
    };
  }

  function render(el, info) {
    if (!el || !info) return;
    el.innerHTML = `<p class="pt-contact-line">
      <a href="${info.mailto}">광고·협업 문의</a>
      <span aria-hidden="true"> · </span>
      <a href="${info.reportUrl}">문의 양식</a>
      <span aria-hidden="true"> · </span>
      <a href="mailto:${info.email}">${info.email}</a>
    </p>`;
  }

  async function mount(el) {
    const info = await fetchContact();
    render(el, info);
  }

  window.ContactFooter = { render: mount, fetchContact };
})();
