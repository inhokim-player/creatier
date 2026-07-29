(function () {
  'use strict';

  const fmt = (n) => `${Math.round(n || 0).toLocaleString('ko-KR')}원`;

  function esc(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function fmtDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  async function loadOverview() {
    const res = await CreatierAuth.apiFetch('/api/admin/overview');
    const data = await res.json();
    if (!data.ok) return;
    document.getElementById('stat-users').textContent = (data.totalUsers ?? 0).toLocaleString('ko-KR');
    document.getElementById('stat-users-today').textContent = (data.todayUsers ?? 0).toLocaleString('ko-KR');
    document.getElementById('stat-net').textContent = fmt(data.totalNet);
    document.getElementById('stat-gross').textContent = fmt(data.totalGross);
    document.getElementById('stat-calcs').textContent = (data.totalCalculations ?? 0).toLocaleString('ko-KR');
    document.getElementById('stat-payable').textContent = fmt(data.totalPayable);
    document.getElementById('stat-inbox-count').textContent = data.pendingReports ?? 0;
  }

  async function loadReports() {
    const res = await CreatierAuth.apiFetch('/api/admin/reports');
    const data = await res.json();
    const list = document.getElementById('reports-list');
    const empty = document.getElementById('inbox-empty');
    if (!data.ok || !data.reports?.length) {
      list.innerHTML = '';
      empty.classList.remove('hidden');
      return;
    }
    empty.classList.add('hidden');
    list.innerHTML = data.reports
      .map(
        (r) =>
          `<li class="pt-list-item pt-admin-inbox-item ${r.status === 'pending' ? 'is-pending' : ''}">
            <div class="pt-list-body">
              <div class="pt-admin-inbox-head">
                <span class="pt-admin-inbox-type">${esc(r.categoryLabel)}</span>
                <span class="pt-admin-inbox-date">${esc(fmtDate(r.createdAt))}</span>
              </div>
              <div class="pt-admin-inbox-body">${esc(r.detail)}</div>
              ${r.contact ? `<div class="pt-admin-inbox-contact">${esc(r.contact)}</div>` : ''}
            </div>
          </li>`
      )
      .join('');
  }

  document.getElementById('btn-logout')?.addEventListener('click', () => CreatierAuth.logout());

  CreatierAuth.requirePlatform()
    .then((me) => {
      if (!me) return;
      loadOverview();
      loadReports();
    })
    .catch(console.error);
})();
