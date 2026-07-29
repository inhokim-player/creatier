(function () {

  'use strict';



  const fmt = (n) => `${Math.round(n || 0).toLocaleString('ko-KR')}원`;

  const token = decodeURIComponent((location.pathname.match(/\/verify\/(.+)/) || [])[1] || '');



  const loading = document.getElementById('verify-loading');

  const pinGate = document.getElementById('verify-pin-gate');

  const body = document.getElementById('verify-body');

  const errBox = document.getElementById('verify-error');

  const errMsg = document.getElementById('verify-error-msg');



  function showError(msg) {

    loading.classList.add('hidden');

    pinGate.classList.add('hidden');

    body.classList.add('hidden');

    errBox.classList.remove('hidden');

    errMsg.textContent = msg;

  }



  function render(data) {

    loading.classList.add('hidden');

    pinGate.classList.add('hidden');

    errBox.classList.add('hidden');

    body.classList.remove('hidden');



    document.title = `${data.creatorName || ''} · 수익 인증`;



    const rows = (data.platforms || [])

      .map(

        (p) => `<div class="pt-calc-card">

          <div class="pt-calc-head">

            ${PlatformIcons.iconBadge(p.platformId, 36)}

            <div><div class="pt-calc-platform">${p.platform}</div><div class="pt-wh-meta">${data.period || ''}${p.verifiedAccount ? ` · @${p.verifiedAccount}` : ''}</div></div>

            <div class="pt-calc-net">${fmt(p.net)}</div>

          </div>

          <div class="pt-calc-lines">

            <div class="pt-calc-line"><span>총수익</span><span>${fmt(p.gross)}</span></div>

            <div class="pt-calc-line"><span>수수료</span><span>- ${fmt(p.platformFee)}</span></div>

            <div class="pt-calc-line"><span>${p.withholdingLabel || '원천징수'}</span><span>${p.withholding > 0 ? `- ${fmt(p.withholding)}` : '없음'}</span></div>

          </div>

        </div>`

      )

      .join('');

    const t = data.totals || {};

    body.innerHTML = `<section class="pt-card pt-card-flush">

      <div class="pt-section-head"><h2>Instagram · TikTok 수익 인증</h2></div>

      <p class="pt-panel-desc">활동명 <strong>${data.creatorName || ''}</strong> · ${data.period || ''}</p>

      <div class="pt-calc-body">${rows}

        <div class="pt-calc-summary">

          <div class="pt-calc-line"><span>합계 실수령</span><span>${fmt(t.net)}</span></div>

        </div>

      </div>

      <div id="verify-share-slot"></div>

    </section>`;



    SocialShare.renderBar(document.getElementById('verify-share-slot'), data, location.href);

  }



  async function load(pin) {

    if (!token) {

      showError('유효하지 않은 링크입니다.');

      return;

    }

    const opts = pin

      ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pin }) }

      : {};

    const res = await fetch(`/api/share/${encodeURIComponent(token)}`, opts);

    const data = await res.json();

    if (!data.ok) {

      if (data.error === 'pin_required') {

        loading.classList.add('hidden');

        pinGate.classList.remove('hidden');

        return;

      }

      showError(data.message || '조회할 수 없습니다.');

      return;

    }

    render(data);

  }



  document.getElementById('verify-pin-btn')?.addEventListener('click', () => {

    const pin = document.getElementById('verify-pin')?.value || '';

    const msg = document.getElementById('verify-pin-msg');

    load(pin).catch(() => {

      if (msg) {

        msg.textContent = '조회 실패';

        msg.classList.remove('hidden');

        msg.style.color = '#f04452';

      }

    });

  });



  ContactFooter.render(document.getElementById('contact-footer-slot'));

  load().catch(() => showError('서버에 연결할 수 없습니다.'));

})();

