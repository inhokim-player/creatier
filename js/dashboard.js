(function () {
  'use strict';

  const fmt = (n) => `${Math.round(n || 0).toLocaleString('ko-KR')}원`;
  const SESSION_ID_KEY = 'creatier_sid';
  let selectedPlatforms = new Set(['youtube_ads']);
  let platformCatalog = [];
  let serverOk = false;

  function sessionId() {
    let id = sessionStorage.getItem(SESSION_ID_KEY);
    if (!id) {
      id = crypto.randomUUID?.() || `s-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      sessionStorage.setItem(SESSION_ID_KEY, id);
    }
    return id;
  }

  function rotateSessionId() {
    const id = crypto.randomUUID?.() || `s-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    sessionStorage.setItem(SESSION_ID_KEY, id);
    return id;
  }

  function creatorName() {
    return (document.getElementById('creator-name')?.value || '').trim();
  }

  function profileSettings() {
    return {
      vatRegistered: !!document.getElementById('vat-registered')?.checked,
    };
  }

  async function checkConnection() {
    if (location.protocol === 'file:') {
      showConnError('Railway URL(https)로 접속하세요.');
      return false;
    }
    try {
      const res = await fetch('/api/health', { cache: 'no-store' });
      if (!res.ok) throw new Error(String(res.status));
      document.getElementById('conn-banner')?.classList.add('hidden');
      serverOk = true;
      return true;
    } catch {
      showConnError('서버에 연결할 수 없습니다. 잠시 후 새로고침 하세요.');
      return false;
    }
  }

  function showConnError(msg) {
    const banner = document.getElementById('conn-banner');
    if (banner) {
      banner.textContent = msg;
      banner.className = 'pt-conn err';
      banner.classList.remove('hidden');
    }
  }

  async function apiFetch(url, options) {
    if (!serverOk && !(await checkConnection())) throw new Error('offline');
    const res = await fetch(url, options);
    let data;
    try {
      data = await res.json();
    } catch {
      throw new Error('invalid_response');
    }
    if (!res.ok && data?.message) throw new Error(data.message);
    return data;
  }

  function collectItems() {
    const items = [];
    document.querySelectorAll('.pt-amount-input').forEach((input) => {
      const gross = Number(input.value);
      if (input.dataset.pid && gross > 0) items.push({ platformId: input.dataset.pid, gross });
    });
    return items;
  }

  function whLine(it) {
    if (it.withholding > 0) {
      const label = it.withholdingLabel || '원천징수';
      return `<div class="pt-calc-line"><span>${label}</span><span>- ${fmt(it.withholding)}</span></div>`;
    }
    return `<div class="pt-calc-line muted"><span>원천징수</span><span>없음 (자진신고)</span></div>`;
  }

  function renderCalcCards(items, totals) {
    const body = document.getElementById('calc-result-body');
    const panel = document.getElementById('calc-result-panel');
    if (!items?.length) {
      panel.classList.add('hidden');
      return;
    }
    panel.classList.remove('hidden');
    body.innerHTML = `${items
      .map((it) => {
        const pid = it.platformId;
        return `<div class="pt-calc-card">
          <div class="pt-calc-head">
            ${PlatformIcons.iconBadge(pid, 36)}
            <div><div class="pt-calc-platform">${it.platform}</div></div>
            <div class="pt-calc-net">${fmt(it.net)}</div>
          </div>
          <div class="pt-calc-lines">
            <div class="pt-calc-line"><span>총수익</span><span>${fmt(it.gross)}</span></div>
            <div class="pt-calc-line"><span>수수료</span><span>- ${fmt(it.platformFee)}</span></div>
            ${whLine(it)}
          </div>
        </div>`;
      })
      .join('')}
      <div class="pt-calc-summary">
        <div class="pt-calc-line"><span>원천징수 합계</span><span>- ${fmt(totals.withholding)}</span></div>
        <div class="pt-calc-line total"><span>순수익 합계</span><span>${fmt(totals.net)}</span></div>
      </div>`;
  }

  function renderHero(s, name) {
    document.getElementById('hero-kpi').hidden = false;
    const nameEl = document.getElementById('hero-creator-name');
    if (name) {
      nameEl.textContent = name;
      nameEl.hidden = false;
    } else {
      nameEl.hidden = true;
    }
    document.getElementById('kpi-ytd-net').textContent = fmt(s.ytdNet);
    document.getElementById('kpi-ytd-gross').textContent = `총수익 ${fmt(s.ytdGross)}`;
    document.getElementById('kpi-payable').textContent = fmt(s.totalPayable);
    document.getElementById('kpi-payable-sub').textContent =
      `종소세 ${fmt(s.comprehensivePayable)} · 부가세 ${fmt(s.annualVat)}`;
    document.getElementById('kpi-fees').textContent = fmt(s.ytdFees);
    document.getElementById('kpi-withholding').textContent = fmt(s.ytdWithholding);
    document.getElementById('kpi-month').textContent = fmt(s.monthlyReserve);

    document.getElementById('hero-tax-detail').hidden = false;
    document.getElementById('tax-basis-note').textContent =
      s.taxBasis || '순수익 기준 간이 추정 · 저장되지 않음';
    const vatRow = s.vatRegistered
      ? `<div class="pt-tax-cell"><span>부가세</span><strong>${fmt(s.annualVat)}</strong></div>`
      : `<div class="pt-tax-cell"><span>부가세</span><strong>미등록</strong></div>`;
    document.getElementById('tax-breakdown').innerHTML = `
      <div class="pt-tax-cell"><span>종소세+지방세</span><strong>${fmt(s.comprehensiveTotal)}</strong></div>
      <div class="pt-tax-cell"><span>원천 공제</span><strong>- ${fmt(s.ytdWithholding)}</strong></div>
      ${vatRow}
      <div class="pt-tax-cell highlight"><span>합계 납부 예상</span><strong>${fmt(s.totalPayable)}</strong></div>`;
  }

  function renderWithholding(wh) {
    const panel = document.getElementById('withholding-panel');
    if (!wh?.byPlatform?.length) {
      panel.hidden = true;
      return;
    }
    panel.hidden = false;
    document.getElementById('withholding-note').textContent =
      wh.note || '지급액 기준 · 종소세 신고 시 원천징수세액 공제';
    document.getElementById('withholding-list').innerHTML = wh.byPlatform
      .map((p) => {
        const amt = p.withholding > 0 ? fmt(p.withholding) : '<span class="pt-wh-none">없음</span>';
        return `<div class="pt-wh-row">
          ${PlatformIcons.iconBadge(p.platformId, 32)}
          <div class="pt-wh-body">
            <div class="pt-wh-title">${p.platform}</div>
            <div class="pt-wh-meta">${p.withholdingLabel || ''} · 총 ${fmt(p.gross)}</div>
          </div>
          <div class="pt-wh-amt">${amt}</div>
        </div>`;
      })
      .join('');
    document.getElementById('withholding-total').innerHTML =
      `<span>원천징수 합계 (종소세 공제)</span><strong>${fmt(wh.totalWithholding)}</strong>`;
  }

  function renderPlatformTax(items) {
    const panel = document.getElementById('platform-tax-panel');
    if (!items?.length) {
      panel.hidden = true;
      return;
    }
    panel.hidden = false;
    document.getElementById('platform-tax-list').innerHTML = items
      .map(
        (p) => `<div class="pt-platform-row">
          ${PlatformIcons.iconBadge(p.platformId, 36)}
          <div class="pt-platform-row-body">
            <div class="pt-platform-row-title">${p.platform}</div>
            <div class="pt-platform-row-meta">총 ${fmt(p.gross)} · 원천 ${p.withholding > 0 ? fmt(p.withholding) : '없음'} · 순 ${fmt(p.net)}</div>
          </div>
          <div class="pt-list-amt">${fmt(p.net)}</div>
        </div>`
      )
      .join('');
  }

  function renderDocItem(d) {
    const where = d.where ? `<em class="pt-doc-where">어디서: ${d.where}</em>` : '';
    const when = d.when ? `<em class="pt-doc-when">언제: ${d.when}</em>` : '';
    return `<div class="pt-doc-item"><span class="pt-doc-dot">•</span><span><strong>${d.title}</strong>${where}${when}<small>${d.desc || ''}</small></span></div>`;
  }

  function renderDocs(docs) {
    const panel = document.getElementById('docs-panel');
    if (!docs?.length) {
      panel.hidden = true;
      return;
    }
    panel.hidden = false;
    let group = '';
    document.getElementById('docs-list').innerHTML = docs
      .map((d) => {
        let head = '';
        if (d.group !== group) {
          group = d.group;
          head = `<div class="pt-doc-group">${group}</div>`;
        }
        return head + renderDocItem(d);
      })
      .join('');
  }

  function renderFiling(items) {
    const panel = document.getElementById('filing-panel');
    if (!items?.length) {
      panel.hidden = true;
      return;
    }
    panel.hidden = false;
    document.getElementById('filing-list').innerHTML = items
      .map(
        (f) =>
          `<li class="pt-list-item"><div class="pt-list-body"><div class="pt-list-amt" style="font-size:0.875rem;">${f.label}</div><div class="pt-list-meta">${f.task}</div></div></li>`
      )
      .join('');
  }

  function renderAlerts(alerts) {
    document.getElementById('alert-banner').innerHTML = (alerts || [])
      .map(
        (a) =>
          `<div class="pt-alert ${a.level === 'warning' ? 'warn' : ''}"><strong>${a.title}</strong><p>${a.message}</p></div>`
      )
      .join('');
  }

  function applyCalcResult(data) {
    const s = data.summary;
    const items = (data.entries || []).map((e) => ({
      platformId: e.platformId,
      platform: e.platform,
      gross: e.gross,
      platformFee: e.platformFee,
      withholding: e.withholding,
      withholdingLabel: e.withholdingLabel,
      net: e.net,
    }));
    const totals = {
      net: s.ytdNet,
      gross: s.ytdGross,
      platformFee: s.ytdFees,
      withholding: s.ytdWithholding,
    };
    renderCalcCards(items, totals);
    renderHero(s, data.creatorName);
    renderWithholding(data.withholding);
    renderPlatformTax(data.byPlatform);
    renderDocs(data.documents);
    renderFiling(data.filingCalendar);
    renderAlerts(data.alerts);
    document.getElementById('calc-result-panel')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function clearInputs() {
    document.getElementById('creator-name').value = '';
    document.querySelectorAll('.pt-amount-input').forEach((i) => {
      i.value = '';
    });
    document.getElementById('entry-submit').disabled = true;
  }

  function resetAll() {
    rotateSessionId();
    clearInputs();
    document.getElementById('conn-banner')?.classList.add('hidden');
    document.getElementById('hero-creator-name').hidden = true;
    document.getElementById('calc-result-panel').classList.add('hidden');
    document.getElementById('hero-kpi').hidden = true;
    document.getElementById('hero-tax-detail').hidden = true;
    document.getElementById('withholding-panel').hidden = true;
    document.getElementById('platform-tax-panel').hidden = true;
    document.getElementById('docs-panel').hidden = true;
    document.getElementById('filing-panel').hidden = true;
    document.getElementById('alert-banner').innerHTML = '';
  }

  async function runPreview() {
    const items = collectItems();
    const name = creatorName();
    document.getElementById('entry-submit').disabled = !(items.length && name.length >= 2);
  }

  async function runCalc() {
    const items = collectItems();
    const name = creatorName();
    if (!items.length || name.length < 2) return;
    const data = await apiFetch('/api/calc', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Session-Id': sessionId() },
      body: JSON.stringify({
        creatorName: name,
        items,
        vatRegistered: profileSettings().vatRegistered,
        sessionId: sessionId(),
      }),
    });
    if (!data.ok) {
      showConnError(data.message || '계산할 수 없습니다.');
      if (data.error === 'session_used') rotateSessionId();
      if (data.error === 'name_limit_reached') {
        document.getElementById('creator-name').value = '';
      }
      return;
    }
    applyCalcResult(data);
    clearInputs();
    rotateSessionId();
    if (data.usage?.nameRemainingToday != null) {
      const left = data.usage.nameRemainingToday;
      const note = left > 0 ? `오늘 이 활동명 ${left}회 더 계산 가능` : '오늘 이 활동명 계산 한도 소진';
      document.getElementById('alert-banner').innerHTML =
        `<div class="pt-alert"><strong>이용 안내</strong><p>${note} · <a href="/terms">약관</a></p></div>`;
    }
  }

  function buildPlatformPicker(platforms) {
    platformCatalog = platforms || [];
    document.getElementById('platform-picker').innerHTML = platformCatalog
      .map(
        (p) =>
          `<button type="button" class="pt-platform-btn ${selectedPlatforms.has(p.id) ? 'active' : ''}" data-pid="${p.id}">
            ${PlatformIcons.iconBadge(p.id, 40)}<span>${PlatformIcons.meta(p.id).label}</span></button>`
      )
      .join('');
    renderAmountInputs();
  }

  function renderAmountInputs() {
    const ids = [...selectedPlatforms];
    const wrap = document.getElementById('platform-amounts');
    if (!ids.length) {
      wrap.innerHTML = '<p class="pt-hint">플랫폼을 선택하세요.</p>';
      return;
    }
    wrap.innerHTML = ids
      .map(
        (pid) =>
          `<div class="pt-amount-row">
            ${PlatformIcons.iconBadge(pid, 28)}
            <span class="pt-amount-label">${PlatformIcons.meta(pid).label}</span>
            <input type="number" class="pt-input pt-amount-input" data-pid="${pid}" placeholder="이번 달 수익 (원)" min="1" inputmode="numeric" />
          </div>`
      )
      .join('');
    runPreview();
  }

  async function loadPlatformDocs() {
    const ids = [...selectedPlatforms];
    if (!ids.length || !serverOk) return;
    try {
      const qs = new URLSearchParams({
        platforms: ids.join(','),
        vatRegistered: profileSettings().vatRegistered ? '1' : '0',
      });
      const data = await apiFetch(`/api/documents/for?${qs}`);
      if (data.ok && data.documents?.length) renderDocs(data.documents);
    } catch {
      /* optional */
    }
  }

  document.getElementById('platform-picker')?.addEventListener('click', (e) => {
    const btn = e.target.closest('.pt-platform-btn');
    if (!btn) return;
    const pid = btn.dataset.pid;
    if (selectedPlatforms.has(pid)) {
      if (selectedPlatforms.size > 1) selectedPlatforms.delete(pid);
    } else {
      selectedPlatforms.add(pid);
    }
    buildPlatformPicker(platformCatalog);
    loadPlatformDocs();
  });

  document.getElementById('platform-amounts')?.addEventListener('input', (e) => {
    if (e.target.matches('.pt-amount-input')) runPreview();
  });

  document.getElementById('creator-name')?.addEventListener('input', runPreview);

  document.getElementById('entry-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('entry-submit');
    if (btn) btn.disabled = true;
    try {
      await runCalc();
    } catch (err) {
      const msg = err?.message === 'offline' ? '서버에 연결할 수 없습니다.' : err?.message || '계산에 실패했습니다.';
      showConnError(msg);
    } finally {
      runPreview();
    }
  });

  document.getElementById('btn-reset')?.addEventListener('click', resetAll);
  document.getElementById('vat-registered')?.addEventListener('change', loadPlatformDocs);

  async function boot() {
    const ok = await checkConnection();
    if (!ok) return;
    try {
      QuickLinks.render(document.getElementById('quick-links-grid'));
      const pdata = await apiFetch('/api/platforms');
      if (pdata.ok) buildPlatformPicker(pdata.platforms);
      loadPlatformDocs();
      ContactFooter.render(document.getElementById('contact-footer-slot'));
    } catch {
      showConnError('화면 로딩 실패. 새로고침(F5) 후 다시 시도하세요.');
    }
  }

  boot();
})();
