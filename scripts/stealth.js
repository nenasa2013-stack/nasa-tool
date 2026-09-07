(function(){
	'use strict';
	try{Object.defineProperty(navigator,'webdriver',{get:()=>false,configurable:true});}catch(e){}
	try{
		const pd=[{name:'Chrome PDF Plugin',filename:'internal-pdf-viewer',description:'Portable Document Format',length:1},{name:'Chrome PDF Viewer',filename:'mhjfbmdgcfjbbpaeojofohoefgiehjai',description:'',length:1},{name:'Native Client',filename:'internal-nacl-plugin',description:'',length:2}];
		Object.defineProperty(navigator,'plugins',{get:()=>pd,configurable:true});
	}catch(e){}
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
