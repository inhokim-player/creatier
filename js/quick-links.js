/** 플랫폼 · 홈택스 바로가기 */
(function (global) {
  'use strict';

  const LINKS = [
    { id: 'youtube_ads', label: 'YouTube', url: 'https://studio.youtube.com' },
    { id: 'instagram', label: 'Instagram', url: 'https://www.instagram.com' },
    { id: 'tiktok', label: 'TikTok', url: 'https://www.tiktok.com/tiktokstudio' },
    { id: 'hometax', label: '홈택스', url: 'https://www.hometax.go.kr', note: '국세청' },
  ];

  const HOMETAX_SVG =
    '<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" style="color:#1b64da"><path fill="currentColor" d="M12 3L2 9v12h7v-7h6v7h7V9L12 3zm0 2.8L18 10v9h-3v-7H9v7H6v-9l6-4.2z"/></svg>';

  function iconFor(link) {
    if (link.id === 'hometax') {
      return `<span class="pf-badge" style="background:#f0f6ff;width:40px;height:40px">${HOMETAX_SVG}</span>`;
    }
    return PlatformIcons.iconBadge(link.id, 40);
  }

  function render(container) {
    if (!container) return;
    container.innerHTML = LINKS.map((link) => {
      const sub = link.note ? `<small>${link.note}</small>` : '';
      return `<a class="pt-quick-link" href="${link.url}" target="_blank" rel="noopener noreferrer">
        ${iconFor(link)}
        <span class="pt-quick-link-text"><strong>${link.label}</strong>${sub}</span>
        <span class="pt-quick-arrow" aria-hidden="true">↗</span>
      </a>`;
    }).join('');
  }

  global.QuickLinks = { render, LINKS };
})(window);
