(() => {
	// 1. Kiểm tra URL đích hợp lệ
	function isFinalDestination(u) {
		if (!u || typeof u !== 'string' || !u.startsWith('http')) return false;
		try {
			var h = new URL(u).hostname.toLowerCase();
			if (h.includes('octolink') || h.includes('uptolink') || h.includes('linkhuongdan') || h.includes('trafficvip') || h.includes('up2link') || h.includes('/check/') || h.includes('example.com') || h.includes('minuc.vn')) return false;
			return true;
		} catch (e) {
			return false;
		}
	}

	// 2. Kết quả từ hook XHR/fetch của engine
	if (window.__OCTO_SOLVE_RESULT__ && window.__OCTO_SOLVE_RESULT__.type) {
		var resData = window.__OCTO_SOLVE_RESULT__.data;
		if (window.__OCTO_SOLVE_RESULT__.type === 'url') {
			if (isFinalDestination(resData)) {
				return JSON.stringify({ type: 'url', data: resData });
			}
			// Nếu là link chuyển tiếp octolink.vip/links/go/..., chuyển hướng tab
			if (resData && resData.includes('links/go') && !window.__htctNavigatedFinish) {
				window.__htctNavigatedFinish = true;
				return JSON.stringify({ type: 'navigate', data: resData });
			}
		} else {
			return JSON.stringify({ type: window.__OCTO_SOLVE_RESULT__.type, data: resData });
		}
	}

	// 3. TỰ ĐỘNG GIẢI TOÁN HỌC CAPTCHA VÒNG TRÒN (OCTO HOLD CAPTCHA / MOVING CIRCLE) - luon giai neu con hold_captcha
	const holdCid = window.HOLD_CAPTCHA_CID;
	const holdInput = document.getElementById('hold_captcha_response') || document.querySelector('input[name="hold_captcha_response"]');
	const hasHoldCaptcha = !!(holdCid && holdInput);
	if (hasHoldCaptcha && !window.__htctHoldStarted) {
		window.__htctHoldStarted = true;

		function decryptChallenge(buf) {
			const magic = "QQ-Encryption";
			const key = "QQ.Encryption|NEW|9999999999999999999";
			const offset = 16;
			const u8 = new Uint8Array(buf);
			let isMagic = true;
			for (let i = 0; i < magic.length; i++) {
				if (u8[i] !== magic.charCodeAt(i)) { isMagic = false; break; }
			}
			if (!isMagic) {
				try { return JSON.parse(new TextDecoder().decode(u8)); } catch (_) { return null; }
			}
			if (u8.length < magic.length + offset * 2) return null;
			const slice = u8.slice(magic.length + offset, u8.length - offset);
			const pre = new Uint8Array(slice.length);
			for (let i = 0; i < slice.length; i++) {
				let b = (slice[i] - 13 + 256) % 256;
				pre[i] = b ^ key.charCodeAt(i % key.length);
			}
			const S = new Array(256);
			for (let i = 0; i < 256; i++) S[i] = i;
			let j = 0;
			for (let i = 0; i < 256; i++) {
				j = (j + S[i] + key.charCodeAt(i % key.length)) % 256;
				const tmp = S[i]; S[i] = S[j]; S[j] = tmp;
			}
			let i_rc4 = 0; j = 0;
			const dec = new Uint8Array(pre.length);
			for (let k = 0; k < pre.length; k++) {
				i_rc4 = (i_rc4 + 1) % 256;
				j = (j + S[i_rc4]) % 256;
				const tmp = S[i_rc4]; S[i_rc4] = S[j]; S[j] = tmp;
				dec[k] = pre[k] ^ S[(S[i_rc4] + S[j]) % 256];
			}
			try { return JSON.parse(new TextDecoder('utf-8').decode(dec)); } catch (_) { return null; }
		}

		function generatePoints(c) {
			const fx1 = c.fx1 || 0.5, fy1 = c.fy1 || 0.5;
			const fx2 = c.fx2 || 0.4, fy2 = c.fy2 || 0.4;
			const px1 = c.px1 || 0,   py1 = c.py1 || 0;
			const px2 = c.px2 || 0,   py2 = c.py2 || 0;
			const w = 448 / 2 - 25, h = 240 / 2 - 25;
			const pts = [];
			for (let t_ms = 0; t_ms <= 1550; t_ms += 16) {
				const t = t_ms / 1000;
				const tx = 224 + w * 0.6 * Math.sin(t * fx1 + px1) + w * 0.4 * Math.sin(t * fx2 + px2);
				const ty = 120 + h * 0.6 * Math.sin(t * fy1 + py1) + h * 0.4 * Math.sin(t * fy2 + py2);
				pts.push([Math.round(t_ms), Math.round(tx + (Math.random() - 0.5)), Math.round(ty + (Math.random() - 0.5))]);
			}
			return JSON.stringify(pts);
		}

		fetch('/api/captcha/init?cid=' + holdCid + '&t=' + Date.now(), { credentials: 'same-origin' })
			.then(r => r.arrayBuffer())
			.then(buf => {
				const challenge = decryptChallenge(buf);
				if (challenge) {
					const payload = generatePoints(challenge);
					holdInput.value = payload;
					window.__htctHoldSolved = true;
					const form = holdInput.closest('form') || document.getElementById('link-view') || document.querySelector('form');
					if (form) {
						setTimeout(() => {
							try { form.requestSubmit ? form.requestSubmit() : form.submit(); } catch (_) {}
						}, 300);
					}
				}
			})
			.catch(() => {});

		return JSON.stringify({ type: 'hold_captcha', text: 'Đang tự động giải mã Captcha vòng tròn...' });
	}

	if (window.__htctHoldSolved && !window.__htctHoldNotified) {
		window.__htctHoldNotified = true;
		return JSON.stringify({ type: 'hold_captcha', text: 'Đã hoàn tất xác thực Captcha vòng tròn! Đang chuyển tiếp...' });
	}

	// 4. Passcode hiển thị trong input[readonly]
	for (const el of document.querySelectorAll('input[readonly]')) {
		const v = (el.value || '').trim();
		if (/^[a-zA-Z0-9]{4,50}$/.test(v) && el.offsetParent) {
			return JSON.stringify({ type: 'code', data: v });
		}
	}


	// 6. XỬ LÝ BƯỚC CUỐI: TRANG FINISH & NÚT LINK GỐC - chi khi het hold_captcha va Link Goc khac trang hien tai
	const _hasHoldForLinkGoc2 = !!(window.HOLD_CAPTCHA_CID && document.getElementById('hold_captcha_response'));
	if (_hasHoldForLinkGoc2) return JSON.stringify({ type: 'idle' });
	const bodyHTML = document.body ? document.body.innerHTML.normalize('NFC') : '';
	const linkGocMatch = bodyHTML.match(/<a[^>]+href=["']([^"']+)["'][^>]*>[^<]*?Link[^<]*?<\/a>/i);
	if (linkGocMatch && linkGocMatch[1]) {
		let targetLink = linkGocMatch[1].trim();
		if (!targetLink.startsWith('http')) {
			try { targetLink = new URL(targetLink, window.location.href).href; } catch (_) {}
		}
		if (targetLink !== window.location.href && targetLink !== window.location.href + '#') {
			return JSON.stringify({ type: 'url', data: targetLink });
		}
	}
	// Quét các thẻ <a> trong trang có chữ "Link Gốc" - chi khi Link Goc khac trang hien tai
	for (const a of document.querySelectorAll('a')) {
		const txt = (a.innerText || a.textContent || '').trim().toLowerCase();
		if (txt === 'link gốc' || txt === 'link goc' || txt.includes('link gốc') || txt.includes('link goc')) {
			let raw = a.href || a.getAttribute('href');
			if (raw && !raw.startsWith('#') && !raw.startsWith('javascript:')) {
				try { raw = new URL(raw, window.location.href).href; } catch (_) {}
				if (raw === window.location.href || raw === window.location.href + '#') continue;
				return JSON.stringify({ type: 'url', data: raw });
			}
		}
	}

	// Fallback cho trang finish: sau khi web tu reload sau khi giai captcha, kiem tra con hold_captcha khong
	if (window.location.pathname.includes('/finish/')) {
		const _stillHasHold2 = !!(window.HOLD_CAPTCHA_CID && document.getElementById('hold_captcha_response'));
		if (_stillHasHold2) {
			return JSON.stringify({ type: 'idle' });
		}
		function isTransientForFinish2(u){
			const l = u.toLowerCase();
			return l.includes('/check/') || l.includes('example.com');
		}
		for (const a of document.querySelectorAll('a')) {
			let raw = a.href || a.getAttribute('href') || a.getAttribute('data-href');
			if (raw && raw.startsWith('http') && !isTransientForFinish2(raw)) {
				if (raw === window.location.href || raw === window.location.href + '#') continue;
				if (raw.includes('/finish/')) continue;
				return JSON.stringify({ type: 'url', data: raw });
			}
		}
		const goForm2 = document.getElementById('go-link') || document.querySelector('form[action*="links/go"]');
		if (goForm2) {
			const inp = goForm2.querySelector('input[name="url"], input[name="link"]');
			if (inp && inp.value && inp.value.startsWith('http') && !isTransientForFinish2(inp.value)) {
				if (inp.value === window.location.href || inp.value === window.location.href + '#') {} else {
					return JSON.stringify({ type: 'url', data: inp.value });
				}
			}
		}
		const allLinks2 = document.body ? document.body.innerHTML.match(/href=["'](https?:\/\/[^"']+)["']/gi) : null;
		if (allLinks2) {
			for (const h of allLinks2) {
				const m = h.match(/href=["'](https?:\/\/[^"']+)["']/i);
				if (m && m[1] && !isTransientForFinish2(m[1])) {
					if (m[1] === window.location.href || m[1] === window.location.href + '#') continue;
					if (m[1].includes('/finish/')) continue;
					return JSON.stringify({ type: 'url', data: m[1] });
				}
			}
		}
	}


	return JSON.stringify({ type: 'idle' });
})();
