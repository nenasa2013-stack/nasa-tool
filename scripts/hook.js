(function(){
	if (window.__octo_hook_installed) return;
	window.__octo_hook_installed = true;
	window.__capturedCodes = [];
	function octoEmit(res){
		window.__OCTO_SOLVE_RESULT__ = res;
		try { window.__capturedCodes.push(JSON.stringify(res)); } catch(e) {}
	}
	function isRealDest(u){
		if (!u || typeof u !== 'string' || u.indexOf('http') !== 0) return false;
		var lower = u.toLowerCase();
		var blocked = ['octolink', 'trafficvip', 'up2link', 'uptolink', 'linkhuongdan', 'huongdan', 'getcode', 'google.com', 'facebook.com', '/check/'];
		for (var k = 0; k < blocked.length; k++) {
			if (lower.indexOf(blocked[k]) >= 0) return false;
		}
		return true;
	}
	function octoCheck(obj){
		if (!obj || typeof obj !== 'object') return false;
		var kc = ['code','passcode','passCode','key'];
		var ku = ['url','destination','redirect','link','target'];
		for (var i = 0; i < kc.length; i++) {
			var v = obj[kc[i]];
			if (typeof v === 'string' && v.length >= 4 && v.length <= 50 && !/^https?:/i.test(v)) { octoEmit({type:'code', data:v}); return true; }
		}
		for (var j = 0; j < ku.length; j++) {
			var u = obj[ku[j]];
			if (isRealDest(u)) { octoEmit({type:'url', data:u}); return true; }
		}
		return false;
	}
	function octoScan(text){
		try {
			if (!text || text.length > 200000) return;
			var j = JSON.parse(text);
			if (!octoCheck(j)) octoCheck(j ? j.data : null);
		} catch(e) {}
	}
	var oxOpen = XMLHttpRequest.prototype.open;
	XMLHttpRequest.prototype.open = function(m, u){ this.__octoUrl = u; return oxOpen.apply(this, arguments); };
	var oxSend = XMLHttpRequest.prototype.send;
	XMLHttpRequest.prototype.send = function(){
		var xhr = this;
		xhr.addEventListener('load', function(){ try { octoScan(xhr.responseText); } catch(e) {} });
		return oxSend.apply(this, arguments);
	};
	if (window.fetch) {
		var oFetch = window.fetch;
		window.fetch = function(){
			var args = arguments;
			var p = oFetch.apply(this, args);
			p.then(function(r){ try { r.clone().text().then(octoScan).catch(function(){}); } catch(e) {} }).catch(function(){});
			return p;
		};
	}
})();
