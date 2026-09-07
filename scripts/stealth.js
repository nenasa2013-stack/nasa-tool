(function(){
	'use strict';
	try{Object.defineProperty(navigator,'webdriver',{get:()=>false,configurable:true});}catch(e){}
	// KHONG fake navigator.plugins: object gia + lech mimeTypes = CreepJS bat 'lies' ngay.
	// De fingerprint moc (headless that) diem cao hon do gia lo.
	try{Object.defineProperty(navigator,'languages',{get:()=>['vi-VN','vi','en-US','en'],configurable:true});}catch(e){}
	try{Object.defineProperty(navigator,'platform',{get:()=>'Win32',configurable:true});}catch(e){}
	try{Object.defineProperty(navigator,'hardwareConcurrency',{get:()=>4,configurable:true});}catch(e){}
	try{Object.defineProperty(navigator,'deviceMemory',{get:()=>8,configurable:true});}catch(e){}
	try{Object.defineProperty(document,'hidden',{get:()=>false,configurable:true});}catch(e){}
	try{Object.defineProperty(document,'visibilityState',{get:()=>'visible',configurable:true});}catch(e){}
	try{Object.defineProperty(document,'referrer',{get:()=>'https://www.google.com/',configurable:true});}catch(e){}
	try{document.cookie='from_google=true; path=/';}catch(e){}
	if(!window.chrome||!window.chrome.runtime){window.chrome={runtime:{onConnect:{addListener:()=>{}},onMessage:{addListener:()=>{}}},loadTimes:function(){return {};},csi:function(){return {};},app:{isInstalled:false}};}
	try{
		const oq=navigator.permissions&&navigator.permissions.query;
		if(oq){navigator.permissions.query=(p)=>p.name==='notifications'?Promise.resolve({state:'default',onchange:null}):oq.call(navigator.permissions,p);}
	}catch(e){}
	try{Object.keys(window).filter(k=>k.startsWith('cdc_')).forEach(k=>{try{delete window[k];}catch(e){}});}catch(e){}
	try{
		['width','height','availWidth','availHeight'].forEach((p,i)=>{
			const v=[1920,1080,1920,1040][i];
			try{Object.defineProperty(screen,p,{get:()=>v,configurable:true});}catch(e){}
		});
		try{Object.defineProperty(screen,'colorDepth',{get:()=>24,configurable:true});}catch(e){}
	}catch(e){}
	try{Object.defineProperty(window,'outerHeight',{get:()=>1080,configurable:true});}catch(e){}
	try{Object.defineProperty(window,'outerWidth',{get:()=>1920,configurable:true});}catch(e){}
})();
