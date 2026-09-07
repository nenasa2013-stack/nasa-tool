// ==UserScript==
// @name         Mobile Emu (fake thiet bi nhu F12)
// @namespace    nasa-tool
// @version      1.0
// @description  Gia lap mobile (iPhone/Pixel/iPad): UA, platform, man hinh, cam ung, client hints. Chay document-start de qua fingerprint.
// @match        *://*/*
// @run-at       document-start
// @grant        GM_registerMenuCommand
// @grant        GM_setValue
// @grant        GM_getValue
// ==/UserScript==

(function () {
  'use strict';

  const DEVICES = {
    'iPhone 14': {
      ua: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
      platform: 'iPhone', vendor: 'Apple Computer, Inc.', maxTouch: 5,
      screen: [390, 844], dpr: 3,
      uad: { mobile: true, platform: 'iOS', brands: ['Not/A)Brand', 'Safari'] }
    },
    'Pixel 7': {
      ua: 'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
      platform: 'Linux armv8l', vendor: 'Google Inc.', maxTouch: 5,
      screen: [412, 915], dpr: 2.625,
      uad: { mobile: true, platform: 'Android', brands: ['Not/A)Brand', 'Chromium'] }
    },
    'iPad Air': {
      ua: 'Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
      platform: 'iPad', vendor: 'Apple Computer, Inc.', maxTouch: 5,
      screen: [820, 1180], dpr: 2,
      uad: { mobile: false, platform: 'iPadOS', brands: ['Not/A)Brand', 'Safari'] }
    }
  };

  let cur = GM_getValue('device', 'iPhone 14');

  function def(obj, prop, value) {
    try { Object.defineProperty(obj, prop, { get: () => value, configurable: true }); return true; }
    catch (e) { return false; }
  }

  function apply(name) {
    const d = DEVICES[name];
    if (!d) return;
    def(window.navigator, 'userAgent', d.ua);
    def(window.navigator, 'appVersion', d.ua.replace('Mozilla/', ''));
    def(window.navigator, 'platform', d.platform);
    def(window.navigator, 'vendor', d.vendor);
    def(window.navigator, 'maxTouchPoints', d.maxTouch);
    def(window, 'devicePixelRatio', d.dpr);
    try {
      Object.defineProperty(window.screen, 'width', { get: () => d.screen[0], configurable: true });
      Object.defineProperty(window.screen, 'height', { get: () => d.screen[1], configurable: true });
      Object.defineProperty(window.screen, 'availWidth', { get: () => d.screen[0], configurable: true });
      Object.defineProperty(window.screen, 'availHeight', { get: () => d.screen[1], configurable: true });
    } catch (e) {}
    try { window.ontouchstart = null; } catch (e) {}
    try {
      if (window.navigator.userAgentData) {
        def(window.navigator, 'userAgentData', {
          brands: d.uad.brands.map(b => ({ brand: b, version: '120' })),
          mobile: d.uad.mobile,
          platform: d.uad.platform,
          getHighEntropyValues: () => Promise.resolve({
            architecture: 'arm', bitness: '64', mobile: d.uad.mobile,
            model: name, platform: d.uad.platform, platformVersion: '16.6'
          })
        });
      }
    } catch (e) {}
    try {
      let badge = document.getElementById('nasa-mobile-badge');
      if (!badge && document.documentElement) {
        badge = document.createElement('div');
        badge.id = 'nasa-mobile-badge';
        badge.textContent = 'MOBILE: ' + name;
        badge.setAttribute('style', 'position:fixed;bottom:8px;right:8px;z-index:2147483647;background:#7c3aed;color:#fff;font:12px sans-serif;padding:4px 8px;border-radius:8px;opacity:.85;pointer-events:none');
        (document.body || document.documentElement).appendChild(badge);
      } else if (badge) badge.textContent = 'MOBILE: ' + name;
    } catch (e) {}
  }

  for (const name of Object.keys(DEVICES)) {
    GM_registerMenuCommand((name === cur ? '● ' : '○ ') + name, () => {
      GM_setValue('device', name);
      location.reload();
    });
  }
  GM_registerMenuCommand('○ TAT (reload)', () => {
    GM_setValue('device', 'OFF');
    location.reload();
  });

  if (cur && cur !== 'OFF') apply(cur);
})();
