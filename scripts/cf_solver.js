/* CF solver (port y tuong tu user solver.js - CHI scan + tag, KHONG click gia).
 * Tim widget Turnstile/CF challenge, tag data-mt-turnstile de Python
 * click THAT bang chuot (isTrusted=true). Ly do khong port click gia:
 * synthetic event isTrusted=false -> an flag programmatic_clicks (dump anti-cheat B2),
 * con forge toString/hook addEventListener -> an flag fn_override (dump T3).
 * Chay document-start qua add_init_script. An toan: chi dat dataset, khong sua DOM.
 */
(() => {
  const SELS = [
    '#turnstile-wrapper', '[id*="turnstile"]',
    'iframe[src*="turnstile"]', 'iframe[src*="challenges.cloudflare"]',
    '.cf-turnstile', '.challenge-container', '#cf-challenge',
    '[data-sitekey]', '.turnstile-container', '.captcha-container',
    'div[class*="turnstile"]', 'div[class*="challenge"]'
  ];
  function inVp(el) {
    try {
      const r = el.getBoundingClientRect();
      if (!r || r.width <= 0 || r.height <= 0) return false;
      const vw = window.innerWidth || 1920, vh = window.innerHeight || 1080;
      return r.bottom > 0 && r.right > 0 && r.left < vw && r.top < vh;
    } catch (e) { return false; }
  }
  function tagBox(el) {
    let box = el;
    try {
      if (el.tagName === 'IFRAME' && el.parentElement) box = el.parentElement;
      const p = box.parentElement;
      if (p && p.id && p.id.indexOf('turnstile') >= 0) box = p;
    } catch (e) {}
    if (!inVp(box)) return false;
    try { box.dataset.mtTurnstile = '1'; } catch (e) { return false; }
    return true;
  }
  function scan() {
    try {
      for (const s of SELS) {
        const els = document.querySelectorAll(s);
        for (const el of els) {
          if (el && !el.hasAttribute('data-mt-turnstile') && tagBox(el)) return true;
        }
      }
    } catch (e) {}
    return false;
  }
  scan();
  // Challenge render lai (delayed) -> tag lai ngay khi xuat hien
  try {
    const obs = new MutationObserver(() => { scan(); });
    const start = () => {
      try {
        if (document.documentElement) {
          obs.observe(document.documentElement, { childList: true, subtree: true });
          return;
        }
      } catch (e) {}
      setTimeout(start, 300);
    };
    start();
  } catch (e) {}
})();
