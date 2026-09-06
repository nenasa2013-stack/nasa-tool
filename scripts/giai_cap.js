// ==UserScript==
// @name         Hold & Moving Circle Captcha Auto-Solver [CỤT TAY X KG]
// @namespace    cuttay.auto.holdcaptcha
// @version      3.3 - Auto Finish & Direct Link Goc Navigator
// @description  Tự động giải mã RC4 Captcha vòng tròn và chuyển hướng Link Gốc tức thì, chống đơ ở trang finish trên Octolink & Uptolink
// @author       Cụt Tay X KG & Antigravity
// @match        *://octolink.vip/*
// @match        *://*.octolink.vip/*
// @match        *://uptolink.vip/*
// @match        *://*.uptolink.vip/*
// @match        *://linkhuongdan.online/*
// @match        *://*.linkhuongdan.online/*
// @match        *://totreview.com/*
// @match        *://*.totreview.com/*
// @match        *://*/*
// @run-at       document-start
// @grant        GM_xmlhttpRequest
// @grant        GM.xmlHttpRequest
// @grant        unsafeWindow
// ==/UserScript==

(function () {
  'use strict';

  // Lấy Window gốc an toàn mà KHÔNG can thiệp làm hỏng native prototype
  const win = typeof unsafeWindow !== 'undefined' ? unsafeWindow : window;

  const curHost = (win.location.hostname || '').toLowerCase();
  const EXCLUDED_HOSTS = [
    'yeutask.com',
    'moneytask.top',
    'cryptolinkforearn.com',
    'kiemkhoai.site',
    'kiemgao.com',
    'minuc.vn',
    'faucetpay.io',
    'google.com',
    'facebook.com',
    'youtube.com',
    'github.com'
  ];

  if (EXCLUDED_HOSTS.some(domain => curHost.includes(domain))) {
    return;
  }

  const CONFIG = {
    showUI: true,
    clickCooldownMs: 2500 // Giãn cách an toàn giữa các lần kích hoạt
  };

  const state = {
    solvedTime: 0,
    octoChallengeSolved: false,
    isActivating: false,
    lastActivateTime: 0,
    lastNavigatedUrl: '',
    activatedElements: new WeakSet()
  };

  // =========================================================================
  // 1. GIAO DIỆN THÔNG BÁO TIẾN TRÌNH CAPTCHA (SAKURA THEME)
  // =========================================================================
  let bannerEl = null;
  function showStatus(text, type = 'info') {
    try {
      var pfx = (type === 'success') ? 'success' : (type === 'error' ? 'error' : (type === 'tracking' ? 'info' : 'info'));
      console.log('[OCTO_PANEL] ' + pfx + ' | ' + text);
    } catch(e) {}
    if (!CONFIG.showUI || !document.body) return;
    if (!bannerEl) {
      bannerEl = document.createElement('div');
      bannerEl.id = '__cuttay_banner';
      Object.assign(bannerEl.style, {
        position: 'fixed',
        top: '20px',
        left: '50%',
        transform: 'translateX(-50%)',
        background: 'linear-gradient(135deg, rgba(35, 12, 38, 0.95), rgba(18, 6, 20, 0.98))',
        color: '#fff0f5',
        padding: '10px 22px',
        borderRadius: '30px',
        border: '1.5px solid rgba(255, 105, 180, 0.65)',
        boxShadow: '0 0 25px rgba(255, 105, 180, 0.5), 0 8px 30px rgba(0,0,0,0.7)',
        zIndex: '2147483647',
        fontFamily: "'Segoe UI', Roboto, sans-serif",
        fontSize: '14px',
        fontWeight: '600',
        letterSpacing: '0.5px',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        pointerEvents: 'none',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
      });
      document.body.appendChild(bannerEl);
    }

    let icon = '🌸';
    let borderColor = 'rgba(255, 105, 180, 0.65)';
    if (type === 'tracking') { icon = '🎯'; borderColor = '#c084fc'; }
    if (type === 'success') { icon = '🏆'; borderColor = '#4ade80'; }
    if (type === 'error') { icon = '💥'; borderColor = '#f87171'; }

    bannerEl.style.borderColor = borderColor;
    bannerEl.innerHTML = `<span style="font-size:18px;">${icon}</span> <span>${text}</span>`;
    bannerEl.style.display = 'flex';
    bannerEl.style.opacity = '1';

    if (type === 'success') {
      setTimeout(() => {
        if (bannerEl) {
          bannerEl.style.opacity = '0';
          setTimeout(() => { if (bannerEl) bannerEl.style.display = 'none'; }, 400);
        }
      }, 4000);
    }
  }

  // =========================================================================
  // 2. GIẢI MÃ THUẬT TOÁN RC4 & TỰ SINH PAYLOAD TỌA ĐỘ CAPTCHA
  // =========================================================================
  function decryptOctoChallenge(buffer) {
    const magic = "QQ-Encryption";
    const key = "QQ.Encryption|NEW|9999999999999999999";
    const offset = 16;
    const u8 = new Uint8Array(buffer);

    let isMagic = true;
    for (let i = 0; i < magic.length; i++) {
      if (u8[i] !== magic.charCodeAt(i)) {
        isMagic = false;
        break;
      }
    }
    if (!isMagic) {
      try {
        return JSON.parse(new TextDecoder().decode(u8));
      } catch (_) {
        return null;
      }
    }

    if (u8.length < magic.length + offset * 2) return null;

    const slice = u8.slice(magic.length + offset, u8.length - offset);
    const pre = new Uint8Array(slice.length);
    for (let i = 0; i < slice.length; i++) {
      let b = (slice[i] - 13 + 256) % 256;
      b = b ^ key.charCodeAt(i % key.length);
      pre[i] = b;
    }

    // RC4 KSA
    const S = new Array(256);
    for (let i = 0; i < 256; i++) S[i] = i;
    let j = 0;
    for (let i = 0; i < 256; i++) {
      j = (j + S[i] + key.charCodeAt(i % key.length)) % 256;
      const tmp = S[i];
      S[i] = S[j];
      S[j] = tmp;
    }

    // RC4 PRGA & Decrypt
    let i_rc4 = 0;
    j = 0;
    const decrypted = new Uint8Array(pre.length);
    for (let k = 0; k < pre.length; k++) {
      i_rc4 = (i_rc4 + 1) % 256;
      j = (j + S[i_rc4]) % 256;
      const tmp = S[i_rc4];
      S[i_rc4] = S[j];
      S[j] = tmp;
      decrypted[k] = pre[k] ^ S[(S[i_rc4] + S[j]) % 256];
    }

    try {
      const jsonStr = new TextDecoder('utf-8').decode(decrypted);
      return JSON.parse(jsonStr);
    } catch (_) {
      return null;
    }
  }

  function generateOctoPayload(challenge) {
    const fx1 = challenge.fx1 || 0.5, fy1 = challenge.fy1 || 0.5;
    const fx2 = challenge.fx2 || 0.4, fy2 = challenge.fy2 || 0.4;
    const px1 = challenge.px1 || 0,   py1 = challenge.py1 || 0;
    const px2 = challenge.px2 || 0,   py2 = challenge.py2 || 0;

    const R3xqr1m = 448; // Chiều rộng vẽ logic của Octolink
    const gDOJPT = 240;  // Chiều cao vẽ logic của Octolink
    const w55Z9d = R3xqr1m / 2 - 25; // 199
    const KumSg2 = gDOJPT / 2 - 25;  // 95

    const points = [];
    const totalDurationMs = 1550; // Giữ > 1500ms theo đúng tiêu chuẩn kiểm duyệt backend
    const intervalMs = 16;        // ~60fps

    for (let t_ms = 0; t_ms <= totalDurationMs; t_ms += intervalMs) {
      const t_sec = t_ms / 1000;
      const targetX = R3xqr1m / 2 +
        w55Z9d * 0.6 * Math.sin(t_sec * fx1 + px1) +
        w55Z9d * 0.4 * Math.sin(t_sec * fx2 + px2);

      const targetY = gDOJPT / 2 +
        KumSg2 * 0.6 * Math.sin(t_sec * fy1 + py1) +
        KumSg2 * 0.4 * Math.sin(t_sec * fy2 + py2);

      const jitterX = (Math.random() - 0.5) * 1.2;
      const jitterY = (Math.random() - 0.5) * 1.2;

      points.push([
        Math.round(t_ms),
        Math.round(targetX + jitterX),
        Math.round(targetY + jitterY)
      ]);
    }

    return JSON.stringify(points);
  }

  function applyOctoSolution(payload) {
    if (state.octoChallengeSolved) return;
    state.octoChallengeSolved = true;
    try{ window.__htctHoldSolved = true; }catch(e){}
    state.solvedTime = Date.now();
    showStatus('🎯 Đã giải mã xong Captcha! Đang nạp kết quả...', 'tracking');

    setTimeout(() => {
      const inputEl = document.getElementById('hold_captcha_response') || document.querySelector('input[name="hold_captcha_response"]');
      if (inputEl) {
        inputEl.value = payload;
      }

      const submitBtn = document.getElementById('invisibleCaptchaShortlink');
      if (submitBtn) {
        submitBtn.style.display = 'inline-block';
        submitBtn.style.pointerEvents = 'auto';
        submitBtn.removeAttribute('disabled');
      }

      // Cho dv (event_id Fingerprint Pro) load xong roi moi submit - tranh reload hoai
      const dvInput = document.getElementById('dv');
      const doSubmit = () => {
        const parentForm = (inputEl && inputEl.closest('form')) || (submitBtn && submitBtn.closest('form')) || document.querySelector('#link-view, form');
        if (parentForm) {
          try {
            parentForm.requestSubmit ? parentForm.requestSubmit() : parentForm.submit();
          } catch (_) {}
        }
      };
      if (dvInput && !dvInput.value) {
        let tries = 0;
        const waitDv = setInterval(() => {
          tries++;
          if (dvInput.value || tries >= 12) {
            clearInterval(waitDv);
            doSubmit();
          }
        }, 500);
      } else {
        doSubmit();
      }

      showStatus('🏆 Đã xác thực Captcha thành công! Đang chuyển sang trang đích...', 'success');
      setTimeout(() => triggerNextStep(), 800);
    }, 300);
  }

  // =========================================================================
  // 3. THỰC HIỆN INIT CAPTCHA BẰNG ISOLATED HTTP (KHÔNG ĐỤNG TỚI WINDOW.FETCH)
  // =========================================================================
  function runPureOctoInit() {
    if (state.octoChallengeSolved) return;
    const cid = win.HOLD_CAPTCHA_CID;
    if (!cid) return;

    const initUrl = `${win.location.origin}/api/captcha/init?cid=${cid}&t=${Date.now()}`;

    const gmXhr = (typeof GM_xmlhttpRequest !== 'undefined' ? GM_xmlhttpRequest : (typeof GM !== 'undefined' && GM.xmlHttpRequest ? GM.xmlHttpRequest : null));
    if (gmXhr) {
      gmXhr({
        method: 'GET',
        url: initUrl,
        responseType: 'arraybuffer',
        onload: function (res) {
          if (res.response) {
            const challenge = decryptOctoChallenge(res.response);
            if (challenge) {
              const payload = generateOctoPayload(challenge);
              applyOctoSolution(payload);
            }
          }
        },
        onerror: function () {
          fallbackFetchInit(initUrl);
        }
      });
    } else {
      fallbackFetchInit(initUrl);
    }
  }

  function fallbackFetchInit(url) {
    fetch(url, { credentials: 'same-origin' })
      .then(res => res.arrayBuffer())
      .then(buf => {
        const challenge = decryptOctoChallenge(buf);
        if (challenge) {
          const payload = generateOctoPayload(challenge);
          applyOctoSolution(payload);
        }
      })
      .catch(() => {});
  }

  // Quét định kỳ để bắt CID của Captcha
  let cidCheckCount = 0;
  const cidInterval = setInterval(() => {
    cidCheckCount++;
    if (win.HOLD_CAPTCHA_CID) {
      clearInterval(cidInterval);
      runPureOctoInit();
    }
    if (cidCheckCount > 40) clearInterval(cidInterval);
  }, 150);

  // =========================================================================
  // 4. TRANG FINISH & NÚT LINK GỐC - KHÔNG BẤM, KHÔNG NAVIGATE KHI LÀ LINK ĐÍCH
  //    Chỉ FETCH URL ra cho Python qua __OCTO_SOLVE_RESULT__ (type url).
  //    Riêng link trung gian (octolink/links/go...) vẫn điều hướng tiếp chuỗi.
  // =========================================================================
  function isTransientDest(u) {
    try {
      const lower = (u || '').toLowerCase();
      const blocked = ['octolink', 'trafficvip', 'up2link', 'uptolink', 'linkhuongdan', 'huongdan',
        'getcode', 'shortearn', 'google.', 'facebook.', 'youtube.', 'zalo.me', 'cloudflare', 'gstatic',
        'moneytask.top', 'yeutask.com'];
      for (let k = 0; k < blocked.length; k++) {
        if (lower.indexOf(blocked[k]) >= 0) return true;
      }
      return false;
    } catch (_) { return true; }
  }

  function emitLinkGoc(targetUrl) {
    try { win.__OCTO_SOLVE_RESULT__ = { type: 'url', data: targetUrl }; } catch (_) {}
    showStatus('🏆 Đã bắt Link Gốc: ' + targetUrl, 'success');
    return true;
  }

  function handleFinishAndLinkGoc() {
    const doc = document;
    if (!doc.body) return false;

    // 1. Quét Regex trực tiếp trong HTML: <a ... href="...">Link Gốc</a>
    //    (body HTML có thể chứa Unicode NFD "G" + dấu combining -> normalize từng đoạn text thay vì cả HTML)
    const regexLinkGoc = /<a[^>]+href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi;
    let anchorMatch;
    while ((anchorMatch = regexLinkGoc.exec(doc.body.innerHTML)) !== null) {
      const anchorText = (anchorMatch[2] || '').replace(/<[^>]*>/g, ' ').normalize('NFC').trim().toLowerCase();
      if (!(anchorText === 'link gốc' || anchorText === 'link goc' || anchorText.includes('link gốc') || anchorText.includes('link goc'))) {
        continue;
      }
      const raw = anchorMatch[1].trim();
      if (raw.startsWith('#') || raw.startsWith('javascript:')) continue;
      const targetUrl = new URL(raw, win.location.href).href;
      if (targetUrl === state.lastNavigatedUrl || targetUrl === win.location.href) continue;
      state.lastNavigatedUrl = targetUrl;
      return emitLinkGoc(targetUrl);
    }

    // 2. Quét thẻ <a> thực tế trong DOM có chữ "Link Gốc" (nút màu xanh như ảnh 1) - chi lay href khong bam
    const allAnchors = doc.querySelectorAll('a');
    for (const a of allAnchors) {
      const text = ((a.innerText || a.textContent || '') + '').normalize('NFC').trim().toLowerCase();
      if (text === 'link gốc' || text === 'link goc' || text.includes('link gốc') || text.includes('link goc')) {
        const href = a.href || a.getAttribute('href') || a.getAttribute('data-href');
        if (href && !href.startsWith('#') && !href.startsWith('javascript:')) {
          const targetUrl = new URL(href, win.location.href).href;
          if (targetUrl !== state.lastNavigatedUrl && targetUrl !== win.location.href) {
            state.lastNavigatedUrl = targetUrl;
            // Chi lay href, khong bam/mo tab - de Python tra ve
            return emitLinkGoc(targetUrl);
          }
        }
      }
    }

    // 3. Quét form #go-link hoặc form /links/go (trung gian -> submit tiếp chuỗi)
    const goForm = doc.getElementById('go-link') || doc.querySelector('form[action*="links/go"], form#go-link');
    if (goForm) {
      const urlInput = goForm.querySelector('input[name="url"], input[name="link"]');
      if (urlInput && urlInput.value && urlInput.value.startsWith('http')) {
        const targetUrl = urlInput.value;
        if (!isTransientDest(targetUrl)) {
          return emitLinkGoc(targetUrl);
        }
        showStatus('🏆 Đang mở liên kết đích...', 'success');
        win.location.href = targetUrl;
        return true;
      }
      if (goForm.action && (goForm.action.includes('links/go') || goForm.action.startsWith('http'))) {
        try {
          goForm.submit();
          return true;
        } catch (_) {}
      }
    }

    return false;
  }

  // =========================================================================
  // 5. BỘ ĐIỀU HƯỚNG CÁC BƯỚC TIẾP THEO (TIẾP TỤC, GET LINK)
  // =========================================================================
  function safeActivateElement(el) {
    if (!el) return;
    const now = Date.now();

    if (el.classList.contains('loading') || el.hasAttribute('disabled') || (now - state.lastActivateTime < CONFIG.clickCooldownMs)) {
      return;
    }

    state.lastActivateTime = now;
    state.isActivating = true;
    state.activatedElements.add(el);

    // 1. Nếu là thẻ <a> có link -> Nhảy thẳng URL không cần chờ click
    const rawHref = el.href || el.getAttribute('href') || el.getAttribute('data-href');
    if (rawHref && !rawHref.startsWith('#') && !rawHref.startsWith('javascript:')) {
      const targetUrl = new URL(rawHref, win.location.href).href;
      if (targetUrl !== win.location.href) {
        showStatus('Đang chuyển hướng...', 'success');
        setTimeout(() => {
          try { win.location.href = targetUrl; } catch (_) {}
        }, 150);
        return;
      }
    }

    // 2. Nếu là submit trong Form -> submit form
    if (el.type === 'submit' && el.form) {
      try {
        el.form.requestSubmit ? el.form.requestSubmit() : el.form.submit();
        return;
      } catch (_) {}
    }

    // 3. Kích hoạt onclick nếu có
    if (typeof el.onclick === 'function') {
      try {
        el.onclick.call(el, { isTrusted: true, target: el, currentTarget: el });
      } catch (_) {}
    }

    // 4. Dispatch Event với isTrusted = true
    try {
      el.removeAttribute('disabled');
      el.style.pointerEvents = 'auto';

      const rect = el.getBoundingClientRect();
      const cx = rect.left + Math.max(5, rect.width / 2);
      const cy = rect.top + Math.max(5, rect.height / 2);

      const ev = new MouseEvent('click', {
        bubbles: true,
        cancelable: true,
        composed: true,
        view: win,
        clientX: cx,
        clientY: cy
      });

      try {
        Object.defineProperty(ev, 'isTrusted', { get: () => true, configurable: true });
      } catch (_) {}

      el.dispatchEvent(ev);
    } catch (_) {}

    // 5. Watchdog giải phóng nút kẹt
    setTimeout(() => {
      state.isActivating = false;
      if (handleFinishAndLinkGoc()) return;

      if (el && el.classList.contains('loading')) {
        el.classList.remove('loading');
        el.removeAttribute('disabled');
        el.style.pointerEvents = 'auto';
      }
    }, 3500);
  }

  function triggerNextStep() {
    const doc = document;
    if (!doc.body) return false;

    // Ưu tiên cao nhất: Kiểm tra và chuyển hướng ngay nếu có Link Gốc (như trang ảnh 1)
    if (handleFinishAndLinkGoc()) return true;

    // Tự động bấm Cloudflare Turnstile nếu có
    const turnstileBox = doc.querySelector('iframe[src*="cloudflare"], iframe[src*="turnstile"], .cf-turnstile');
    if (turnstileBox && !turnstileBox.__cuttayClicked) {
      turnstileBox.__cuttayClicked = true;
      try {
        const checkbox = turnstileBox.contentDocument ? turnstileBox.contentDocument.querySelector('input[type="checkbox"], .cb-c') : null;
        if (checkbox) {
          const ev = new MouseEvent('click', { bubbles: true, cancelable: true, view: win });
          try { Object.defineProperty(ev, 'isTrusted', { get: () => true }); } catch (_) {}
          checkbox.dispatchEvent(ev);
        }
      } catch (_) {}
    }

    // Quét các nút bấm hành động (NHẬN ĐỂ TIẾP TỤC, GET LINK, v.v.)
    if (state.isActivating || Date.now() - state.lastActivateTime < CONFIG.clickCooldownMs) {
      return false;
    }

    const candidates = Array.from(doc.querySelectorAll('a.btn, button.btn, .btn-captcha, #btn-main, .get-link, button[type="submit"], a[href]'));
    for (const el of candidates) {
      if (state.activatedElements.has(el)) continue;

      const text = ((el.innerText || el.textContent || el.value || '') + '').normalize('NFC').trim().toLowerCase();
      if (text.includes('vui lòng đợi') || text.includes('waiting') || text.includes('bắt đầu ...')) {
        continue;
      }

      const isLinkGoc = text.includes('link gốc') || text.includes('link goc');
      const isNextBtn = text.includes('tiếp tục') || text.includes('nhận để tiếp tục') || text.includes('get link') || text.includes('lấy link') || el.id === 'btn-main' || el.classList.contains('get-link');

        if (isLinkGoc || isNextBtn) {
        const style = getComputedStyle(el);
        if (style.display !== 'none' && style.visibility !== 'hidden') {
          // Link Gốc -> CHI LAY HREF KHONG BAM
          if (isLinkGoc) {
            const href = el.href || el.getAttribute('href') || el.getAttribute('data-href');
            if (href && !href.startsWith('#') && !href.startsWith('javascript:')) {
              const targetUrl = new URL(href, win.location.href).href;
              state.activatedElements.add(el);
              return emitLinkGoc(targetUrl);
            }
          }
          showStatus(`Đang mở [${(el.innerText || el.textContent || 'Tiếp tục').trim()}]...`, 'success');
          safeActivateElement(el);
          return true;
        }
      }
    }
    return false;
  }

  // Quét định kỳ kiểm tra nút mỗi 800ms
  setInterval(() => {
    triggerNextStep();
  }, 800);

  const observer = new MutationObserver(() => {
    if (win.HOLD_CAPTCHA_CID && !state.octoChallengeSolved) {
      runPureOctoInit();
    }
    handleFinishAndLinkGoc();
  });

  if (document.body) {
    observer.observe(document.body, { childList: true, subtree: true });
  } else {
    document.addEventListener('DOMContentLoaded', () => {
      if (document.body) observer.observe(document.body, { childList: true, subtree: true });
    });
  }

  // Tự động kiểm tra ngay khi load script
  if (win.location.pathname.includes('/finish/')) {
    setTimeout(handleFinishAndLinkGoc, 200);
  }

  console.log('[🌸 Cụt Tay X KG] 🎯 Phiên bản v3.3 (Auto Finish & Direct Link Gốc) đã sẵn sàng!');
})();
