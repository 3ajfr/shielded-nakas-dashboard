// The Vault — Activity: recent SALES with filters (tier, traits, Shielded # bucket, period, sort). Additive module, scoped "ac-" CSS.
// Data: public secondary-market trades via the CORS edge mirror (no API key, 0 Ord Dropz key units); falls back to data.json lastSales.
(()=>{
const css=`#acp{display:none;position:fixed;inset:64px 10px 10px;overflow:auto;z-index:8;background:var(--k);color:var(--cr);border:3px solid var(--o);padding:14px 16px;box-shadow:6px 6px 0 #000;font-family:SG,sans-serif}
#acp.on{display:block}
#acp .ac-h{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}#acp .ac-h h2{margin:0;font:40px Anton,sans-serif;color:var(--o);text-shadow:3px 3px 0 #000}
#acp .ac-sum{font-size:13px}#acp .ac-sum b{font:16px Anton,sans-serif;color:var(--o);letter-spacing:.03em}
#acp .ac-f{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;margin:10px 0;padding:8px 0;border-top:2px dashed rgba(242,106,27,.5);border-bottom:2px dashed rgba(242,106,27,.5)}
#acp .ac-g{display:flex;flex-wrap:wrap;align-items:center;gap:2px}#acp .ac-g>span{font:13px Anton,sans-serif;letter-spacing:.05em;color:#b8ab92;margin-right:4px}
#acp select{font:13px SG,sans-serif;font-weight:700;background:#1b1612;color:var(--cr);border:2px solid #4a423a;border-radius:3px;padding:3px 6px;max-width:200px}
#acp .tfb{margin:0}
.ac-r{display:grid;grid-template-columns:56px 1fr auto;gap:12px;align-items:center;padding:8px 6px;border-bottom:1px dashed rgba(242,106,27,.35)}
.ac-r:hover{background:#1b1612}
.ac-r img{width:56px;height:56px;image-rendering:pixelated;border:2px solid #000;background:var(--o)}
.ac-r .t{font:20px Anton,sans-serif;letter-spacing:.02em}.ac-r .m{font-size:12px;color:#cfc3ab}.ac-r .m i{font-style:normal;display:inline-block;width:9px;height:9px;border:1px solid #000;margin-right:3px}
.ac-r .p{text-align:right}.ac-r .p b{font:20px Anton,sans-serif;color:var(--o);display:block}.ac-r .p small{display:block;font-size:12px;color:#b8ab92}
.ac-r .a{display:flex;gap:8px;justify-content:flex-end;margin-top:4px;font-size:12px}.ac-r .a a{color:var(--cr);font-weight:700}.ac-r .a button{font-size:12px;padding:1px 7px}
#acp .ac-more{display:block;margin:14px auto 4px}#acp .ac-note{font-size:11px;color:#8a7e68;margin-top:10px}
html.mob #acp.pane{padding:12px 12px 24px;box-shadow:none;border-left:0;border-right:0}
html.mob #acp .ac-h h2{font-size:32px}html.mob #acx{display:none}
html.mob #acp .ac-f{flex-wrap:nowrap;flex-direction:column;align-items:stretch;gap:8px}
html.mob #acp .ac-g{flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none;-webkit-overflow-scrolling:touch}html.mob #acp .ac-g::-webkit-scrollbar{display:none}
html.mob #acp .chip{min-height:34px;flex:0 0 auto;white-space:nowrap}
html.mob #acp select{min-height:40px;font-size:15px;flex:1;max-width:none}
html.mob #acp .tf{font-size:16px;padding:8px 0;flex:1;text-align:center}html.mob #acp .tfb{width:100%}
html.mob .ac-r{grid-template-columns:52px 1fr;gap:10px}html.mob .ac-r img{width:52px;height:52px}
html.mob .ac-r .p{grid-column:1/3;text-align:left;display:flex;flex-wrap:wrap;align-items:center;gap:4px 10px}html.mob .ac-r .p b{display:inline}
html.mob .ac-r .a{margin:0 0 0 auto}html.mob .ac-r .a a,html.mob .ac-r .a button{min-height:40px;display:inline-flex;align-items:center;padding:0 10px}`;
const TIERS=['Legendary','Epic','Rare','Uncommon','Common'],TCOL={Legendary:'#f3ead6',Epic:'#f26a1b',Rare:'#ffa451',Uncommon:'#9c4a17',Common:'#4a423a'};
const SUBS=[['sub10','SUB10'],['sub100','SUB100'],['sub1k','SUB1K'],['other','OTHER']];
const PER=[['24h','24H',1],['7d','7D',7],['30d','30D',30],['all','ALL',0]];
const st={per:'7d',sort:'new',tiers:new Set(),subs:new Set(),tt:'',tv:'',show:100};
let el=null,sales=null,loadedAt=0,loading=null,src='';
const V=()=>window.VAULT||{};
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const subOf=it=>['sub10','sub100','sub1k'].includes(it.sub)?it.sub:'other';
const mob=()=>document.documentElement.classList.contains('mob');
function ago(t){const s=(Date.now()-t)/1000;if(s<90)return 'just now';if(s<3600)return Math.round(s/60)+' min ago';if(s<86400)return Math.round(s/3600)+' h ago';return Math.round(s/86400)+' d ago';}
const when=t=>new Date(t).toLocaleString([], {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',hour12:false});
async function load(){
 if(sales&&Date.now()-loadedAt<120000)return;if(loading)return loading;
 loading=(async()=>{const v=V(),byId=new Map((v.items||[]).map(i=>[i.id,i]));
  try{const ac=new AbortController(),tm=setTimeout(()=>ac.abort(),8000);
   const r=await (await fetch((v.LIVE||'')+'/sales',{signal:ac.signal,cache:'no-store'})).json();clearTimeout(tm);
   if(!r||!Array.isArray(r.s))throw 0;
   sales=r.s.map(([id,p,at,tx])=>({it:byId.get(id),p:+p,t:Date.parse(at),tx})).filter(x=>x.it&&x.p>0&&x.t);src='live';}
  catch(e){if(!sales){const ls=(v.D&&v.D.lastSales)||[];sales=ls.map(x=>({it:v.byNo&&v.byNo.get(+x.no),p:+x.p,t:Date.parse(x.at)})).filter(x=>x.it&&x.p&&x.t);src='cached';}}
  loadedAt=Date.now();loading=null;})();
 return loading;}
function filtered(){const per=PER.find(x=>x[0]==st.per),since=per[2]?Date.now()-per[2]*864e5:0;
 const r=sales.filter(x=>x.t>=since&&(!st.tiers.size||st.tiers.has(x.it.tier))&&(!st.subs.size||st.subs.has(subOf(x.it)))&&(!st.tt||!st.tv||(x.it.traits||{})[st.tt]==st.tv));
 const so={new:(a,b)=>b.t-a.t,old:(a,b)=>a.t-b.t,hi:(a,b)=>b.p-a.p||b.t-a.t,lo:(a,b)=>a.p-b.p||b.t-a.t}[st.sort];return r.sort(so);}
function traitTypes(){const m=new Map();(V().items||[]).forEach(i=>Object.entries(i.traits||{}).forEach(([k,v])=>{if(!m.has(k))m.set(k,new Map());const mm=m.get(k);mm.set(v,(mm.get(v)||0)+1);}));return m;}
let TT=null;
function render(){if(!el)return;const v=V(),P=v.P||(s=>s),img=v.img||(()=>'');
 if(!sales){el.innerHTML=`<div class="ac-h"><h2>ACTIVITY</h2><button class="dark" id="acx">✕ Back to vault</button></div><p>Loading sales…</p>`;bind();return;}
 TT=TT||traitTypes();const rows=filtered(),vol=rows.reduce((a,x)=>a+x.p,0),ps=rows.map(x=>x.p).sort((a,b)=>a-b),med=ps.length?ps[ps.length>>1]:null;
 const chip=(on,label,data,col)=>`<span class="chip${on?' on':''}" ${data}>${col?`<i style="background:${col}"></i>`:''}${label}</span>`;
 const vals=st.tt&&TT.get(st.tt)?[...TT.get(st.tt).entries()].sort((a,b)=>a[0].localeCompare(b[0])):[];
 el.innerHTML=`<div class="ac-h"><h2>ACTIVITY</h2><span class="ac-sum"><b>${rows.length}</b> sale${rows.length==1?'':'s'} · volume <b>${P(vol)}</b>${med!=null?` · median <b>${P(med)}</b>`:''}</span><button class="dark" id="acx">✕ Back to vault</button></div>
 <div class="ac-f">
  <div class="ac-g"><span>PERIOD</span><div class="tfb">${PER.map(([k,l])=>`<span class="tf${k==st.per?' on':''}" data-per="${k}">${l}</span>`).join('')}</div></div>
  <div class="ac-g"><span>SORT</span><select id="acs"><option value="new">Newest first</option><option value="old">Oldest first</option><option value="hi">Price: high → low</option><option value="lo">Price: low → high</option></select></div>
  <div class="ac-g"><span>TIER</span>${TIERS.map(t=>chip(st.tiers.has(t),t,`data-tier="${t}"`,TCOL[t])).join('')}</div>
  <div class="ac-g"><span>SHIELDED #</span>${SUBS.map(([k,l])=>chip(st.subs.has(k),l,`data-sub="${k}"`)).join('')}</div>
  <div class="ac-g"><span>TRAIT</span><select id="actt"><option value="">Any trait type</option>${[...TT.keys()].map(k=>`<option${k==st.tt?' selected':''}>${esc(k)}</option>`).join('')}</select>
   <select id="actv"${st.tt?'':' disabled'}><option value="">Any value</option>${vals.map(([k,n])=>`<option value="${esc(k)}"${k==st.tv?' selected':''}>${esc(k)} (${n})</option>`).join('')}</select></div>
  ${(st.tiers.size||st.subs.size||st.tv)?'<span class="chip clr" id="acclr">✕ Clear</span>':''}
 </div><div id="acl">${rows.length?'':'<p>No sale matches these filters in this period.</p>'}${rows.slice(0,st.show).map(x=>{const it=x.it;return `<div class="ac-r"><img loading="lazy" src="${img(it)}" alt="">
  <div><div class="t">NAKAS #${it.no}</div><div class="m"><i style="background:${TCOL[it.tier]||'#333'}"></i>${it.tier} · rank ${it.rank} · ${it.sub} · Shielded # ${it.num}</div></div>
  <div class="p"><b>${P(x.p)}</b><small title="${when(x.t)}">${ago(x.t)} · ${when(x.t)}</small><div class="a"><button class="dark" data-v="${it.no}">View in vault</button><a target="_blank" rel="noopener" href="https://ordinals.com/inscription/${it.id}">Inscription ↗</a></div></div></div>`}).join('')}
 ${rows.length>st.show?`<button class="dark ac-more" id="acm">Show more (${rows.length-st.show} left)</button>`:''}</div>
 <div class="ac-note">${src=='live'?'Live sales from the public Shielded secondary market · refreshed every ~2 min.':'Live sales unavailable right now · showing the latest sales from the vault data.'} Times in your local time zone.</div>`;
 el.querySelector('#acs').value=st.sort;bind();}
function bind(){const q=s=>el.querySelector(s);q('#acx').onclick=()=>close(true);if(!sales)return;
 el.querySelectorAll('[data-per]').forEach(b=>b.onclick=()=>{st.per=b.dataset.per;st.show=100;render();});
 el.querySelectorAll('[data-tier]').forEach(b=>b.onclick=()=>{const t=b.dataset.tier;st.tiers.has(t)?st.tiers.delete(t):st.tiers.add(t);st.show=100;render();});
 el.querySelectorAll('[data-sub]').forEach(b=>b.onclick=()=>{const t=b.dataset.sub;st.subs.has(t)?st.subs.delete(t):st.subs.add(t);st.show=100;render();});
 q('#acs').onchange=e=>{st.sort=e.target.value;render();};
 q('#actt').onchange=e=>{st.tt=e.target.value;st.tv='';render();};q('#actv').onchange=e=>{st.tv=e.target.value;st.show=100;render();};
 const c=q('#acclr');if(c)c.onclick=()=>{st.tiers.clear();st.subs.clear();st.tt='';st.tv='';render();};
 const m=q('#acm');if(m)m.onclick=()=>{st.show+=100;render();};
 el.querySelectorAll('button[data-v]').forEach(b=>b.onclick=()=>{const v=V(),it=v.byNo&&v.byNo.get(+b.dataset.v);close(true);if(it&&v.card){v.card(it);v.flyTo([it.no]);}});}
function ensure(){if(el)return;const s=document.createElement('style');s.textContent=css;document.head.appendChild(s);
 el=document.createElement('div');el.id='acp';el.className='hud panel';el.setAttribute('role','dialog');el.setAttribute('aria-label','Activity: recent sales');document.body.appendChild(el);}
async function open(fromTab){ensure();el.classList.add('on');if(mob())el.classList.add('pane');el.scrollTop=0;render();await load();render();}
function close(back){if(!el)return;el.classList.remove('on','pane');if(back&&mob()){const b=document.querySelector('#mtabs button[data-t="vault"]');if(b&&!document.body.classList.contains('t-vault'))b.click();}}
function toggle(){el&&el.classList.contains('on')?close():open();}
function init(){const b=document.getElementById('actBtn');if(b)b.onclick=toggle;}
document.readyState=='loading'?document.addEventListener('DOMContentLoaded',init):init();
window.VaultActivity={open,close,toggle,get sales(){return sales}};
})();
