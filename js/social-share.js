(function () {
  'use strict';

  const fmt = (n) => `${Math.round(n || 0).toLocaleString('ko-KR')}원`;

  const LINKS = {
    instagram: {
      label: 'Instagram',
      web: 'https://www.instagram.com/',
      mobile: 'instagram://app',
    },
    tiktok: {
      label: 'TikTok',
      web: 'https://www.tiktok.com/tiktokstudio',
      mobile: 'snssdk1233://feed',
    },
  };

  function isMobile() {
    return /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
  }

  function buildShareText(data, pageUrl) {
    const url = pageUrl || location.href;
    const lines = [`[크라잇에이터 수익 인증]`, `${data.creatorName || ''} · ${data.period || ''}`, ''];
    (data.platforms || []).forEach((p) => {
      lines.push(`${p.platform}: 실수령 ${fmt(p.net)} (총 ${fmt(p.gross)})`);
    });
    if (data.totals?.net) {
      lines.push('', `합계 실수령 ${fmt(data.totals.net)}`);
    }
    lines.push('', url);
    return lines.join('\n');
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(ta);
      return ok;
    }
  }

  function openExternal(url) {
    const a = document.createElement('a');
    a.href = url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.click();
  }

  function tryAppThenWeb(mobileUrl, webUrl) {
    if (isMobile()) {
      const start = Date.now();
      window.location.href = mobileUrl;
      setTimeout(() => {
        if (Date.now() - start < 2200) openExternal(webUrl);
      }, 1500);
    } else {
      openExternal(webUrl);
    }
  }

  async function shareToPlatform(platformId, data, pageUrl) {
    const spec = LINKS[platformId];
    if (!spec) return false;
    const text = buildShareText(data, pageUrl);
    await copyText(text);
    tryAppThenWeb(spec.mobile, spec.web);
    return true;
  }

  async function nativeShare(data, pageUrl) {
    const url = pageUrl || location.href;
    const text = buildShareText(data, url);
    if (!navigator.share) return false;
    try {
      await navigator.share({
        title: `${data.creatorName || ''} 수익 인증`,
        text,
        url,
      });
      return true;
    } catch {
      return false;
    }
  }

  function renderBar(container, data, pageUrl) {
    if (!container || !data) return;
    const url = pageUrl || location.href;
    const hasIg = (data.platforms || []).some((p) => p.platformId === 'instagram');
    const hasTt = (data.platforms || []).some((p) => p.platformId === 'tiktok');
    const parts = [];
    if (hasIg) {
      parts.push(`<button type="button" class="pt-vshare-btn pt-vshare-ig" data-platform="instagram">Instagram 공유</button>`);
    }
    if (hasTt) {
      parts.push(`<button type="button" class="pt-vshare-btn pt-vshare-tt" data-platform="tiktok">TikTok 공유</button>`);
    }
    parts.push(`<button type="button" class="pt-vshare-btn pt-vshare-copy" data-action="copy">링크 복사</button>`);
    if (navigator.share) {
      parts.push(`<button type="button" class="pt-vshare-btn pt-vshare-native" data-action="native">더 공유하기</button>`);
    }
    container.innerHTML = `<div class="pt-vshare-bar">${parts.join('')}</div>
      <p class="pt-vshare-hint hidden" id="vshare-hint"></p>`;

    const hint = container.querySelector('#vshare-hint');
    function flash(msg) {
      if (!hint) return;
      hint.textContent = msg;
      hint.classList.remove('hidden');
      setTimeout(() => hint.classList.add('hidden'), 2500);
    }

    container.querySelectorAll('[data-platform]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const pid = btn.dataset.platform;
        await shareToPlatform(pid, data, url);
        flash(`${LINKS[pid].label} 열림 · 내용 복사됨`);
      });
    });
    container.querySelector('[data-action="copy"]')?.addEventListener('click', async () => {
      await copyText(url);
      flash('링크 복사됨');
    });
    container.querySelector('[data-action="native"]')?.addEventListener('click', async () => {
      const ok = await nativeShare(data, url);
      if (!ok) flash('공유를 취소했습니다');
    });
  }

  window.SocialShare = {
    buildShareText,
    shareToPlatform,
    nativeShare,
    renderBar,
    copyText,
  };
})();
