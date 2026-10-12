// $SHNAKAS rewards timeline (block 971,700) — additive module, scoped "tl-" CSS
(function(){'use strict';
const TARGET=971700,START=969000,TICKS=[[-1000,'-1000'],[-500,'-500'],[-144,'~1 DAY'],[-6,'~1 H'],[0,'REWARDS START']];
const css=`
.tl-pill{position:fixed;z-index:6;left:10px;bottom:26px;display:flex;align-items:center;gap:6px;background:#0d0b09;color:#f3ead6;border:2px solid #f26a1b;box-shadow:3px 3px 0 #000;padding:4px 10px;font:14px Anton,Impact,sans-serif;letter-spacing:.04em;cursor:pointer;min-height:32px;border-radius:3px}
.tl-pill:hover{background:#f26a1b;color:#000}.tl-pill b{color:#f26a1b;font-weight:400}.tl-pill:hover b{color:#000}
body.landing .tl-pill,#res[style*="block"]~.tl-pill{display:none}
html.mob .tl-pill{left:8px;bottom:calc(58px + env(safe-area-inset-bottom) + 8px);min-height:40px;font-size:15px}
.tl-ov{position:fixed;inset:0;z-index:60;background:rgba(0,0,0,.6);display:none;align-items:center;justify-content:center;padding:12px}
.tl-ov.tl-on{display:flex}
.tl-panel{width:min(720px,96vw);max-height:92vh;overflow:auto;background:rgba(13,11,9,.97);border:3px solid #f26a1b;box-shadow:8px 8px 0 #000;color:#f3ead6;font:13px SG,system-ui,sans-serif;padding:4px 4px 12px;animation:tl-in .25s ease-out}
.tl-panel{position:relative}.tl-panel .tl-row{flex-wrap:wrap;white-space:normal;padding-right:58px}.tl-panel .tl-x{position:absolute;top:6px;right:6px;z-index:2}
@keyframes tl-in{from{transform:translateY(16px);opacity:0}}
.tl-x{margin-left:auto;font:18px Anton,Impact,sans-serif;background:#f3ead6;color:#000;border:2px solid #000;min-width:40px;min-height:40px;cursor:pointer;box-shadow:2px 2px 0 #000}
html.mob .tl-ov{align-items:flex-end;padding:0}
html.mob .tl-panel{width:100%;max-height:85vh;border-radius:16px 16px 0 0;border-bottom:0;padding-bottom:calc(16px + env(safe-area-inset-bottom));animation:tl-up .3s cubic-bezier(.2,1,.3,1)}
@keyframes tl-up{from{transform:translateY(100%)}}
html.mob .tl-x{min-width:48px;min-height:48px}
html.mob .tl-grid{grid-template-columns:1fr 1fr}
.tl-row{display:flex;align-items:center;gap:10px;padding:6px 10px;white-space:nowrap;overflow:hidden}
.tl-tag{background:#000;color:#f26a1b;font:15px Anton,Impact,sans-serif;letter-spacing:.04em;padding:2px 8px;border:1px solid #f26a1b;transform:rotate(-1.5deg)}
.tl-cd{font:20px Anton,Impact,sans-serif;letter-spacing:.03em;color:#fff}.tl-cd i{font-style:normal;color:#f26a1b;font-size:13px;margin:0 3px 0 1px}
.tl-mini{flex:1;min-width:60px;height:8px;background:#2a221b;border:1px solid #000;position:relative;overflow:hidden}.tl-mini b{position:absolute;left:0;top:0;bottom:0;background:linear-gradient(90deg,#f26a1b,#d81e1e)}
.tl-sm{color:#b8ab92;font-size:12px}
.tl-exp{padding:4px 12px 4px;border-top:2px dashed rgba(242,106,27,.5)}
.tl-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:8px 0}
.tl-grid div{background:#f3ead6;color:#000;border:2px solid #000;box-shadow:3px 3px 0 #000;padding:4px 8px}.tl-grid span{display:block;font-size:11px;font-weight:700;color:#3b1a05}.tl-grid b{font:20px Anton,Impact,sans-serif}
.tl-bar{position:relative;height:56px;margin:14px 6px 4px}
.tl-track{position:absolute;left:0;right:0;top:18px;height:12px;background:#2a221b;border:2px solid #000;background-image:repeating-linear-gradient(90deg,transparent 0 9px,rgba(242,106,27,.15) 9px 10px)}
.tl-fill{position:absolute;left:0;top:18px;height:12px;background:linear-gradient(90deg,#f26a1b,#d81e1e);border:2px solid #000;box-shadow:0 0 10px rgba(242,106,27,.7)}
.tl-now{position:absolute;top:12px;width:24px;height:24px;margin-left:-12px;border-radius:50%;background:#d81e1e;border:3px solid #000;box-shadow:0 0 0 0 rgba(216,30,30,.8);animation:tl-p 1.6s infinite}
@keyframes tl-p{70%{box-shadow:0 0 0 14px rgba(216,30,30,0)}100%{box-shadow:0 0 0 0 rgba(216,30,30,0)}}
.tl-tk{position:absolute;top:10px;width:2px;height:28px;background:#f3ead6;margin-left:-1px}.tl-tk em{position:absolute;top:30px;left:50%;transform:translateX(-50%);font:11px Anton,Impact,sans-serif;font-style:normal;white-space:nowrap;color:#f3ead6}
.tl-tk.tl-t{background:#f26a1b;width:4px;margin-left:-2px;height:34px;top:7px}.tl-tk.tl-t em{color:#000;background:#f26a1b;padding:0 5px;border:1px solid #000;top:36px}
.tl-tk.tl-l em{left:0;transform:none}.tl-tk.tl-r em{left:auto;right:0;transform:none}
.tl-live{color:#2bd46a!important}
.tl-stk{position:absolute;z-index:3;top:62px;right:22px;background:#d81e1e;color:#fff;border:3px solid #000;box-shadow:4px 4px 0 #000;padding:4px 12px;font:18px Anton,Impact,sans-serif;letter-spacing:.03em;transform:rotate(2deg);text-align:center;line-height:1.1}
.tl-stk small{display:block;font:11px SG,system-ui,sans-serif;font-weight:700;color:#ffd9c7}
html.mob .tl-stk{top:calc(env(safe-area-inset-top) + 52px);right:12px;font-size:15px}
.tl-mob{margin:0 0 12px;background:#0d0b09;border:2px solid #f26a1b;padding:8px 10px;color:#f3ead6;box-shadow:4px 4px 0 rgba(242,106,27,.35)}
.tl-mob .tl-grid{grid-template-columns:1fr 1fr}.tl-mob .tl-cd{font-size:26px}
`;
const s=document.createElement('style');s.textContent=css;document.head.appendChild(s);
let tip=null,avg=600,tipAt=Date.now(),err=false;
const fmtN=n=>n.toLocaleString('en');
async function getTip(){for(const u of['https://mempool.space/api/blocks/tip/height','https://blockstream.info/api/blocks/tip/height']){
  try{const r=await fetch(u,{cache:'no-store'});if(!r.ok)continue;const v=parseInt(await r.text(),10);if(v>0){if(v!==tip)tipAt=Date.now();tip=v;err=false;return;}}catch(e){}}err=true;}
async function getAvg(){try{const r=await fetch('https://mempool.space/api/v1/blocks');const b=await r.json();if(b.length>3){const a=(b[0].timestamp-b[b.length-1].timestamp)/(b.length-1);if(a>300&&a<1200)avg=a;}}catch(e){}}
function calc(){if(tip==null)return null;const left=Math.max(0,TARGET-tip);const eta=Date.now()+left*avg*1000-Math.min(Date.now()-tipAt,left?avg*1000:0);
 const ms=Math.max(0,eta-Date.now());return{left,eta:new Date(eta),ms,live:left<=0,pct:Math.min(1,Math.max(0,(tip-START)/(TARGET-START)))};}
function cd(ms){const m=Math.floor(ms/60000),d=Math.floor(m/1440),h=Math.floor(m%1440/60),mi=m%60,se=Math.floor(ms/1000)%60;return `${d}<i>D</i>${String(h).padStart(2,'0')}<i>H</i>${String(mi).padStart(2,'0')}<i>M</i>${String(se).padStart(2,'0')}<i>S</i>`;}
function bar(c){const pos=b=>((b-START)/(TARGET-START)*100);
 return `<div class="tl-bar"><div class="tl-track"></div><div class="tl-fill" style="width:${c.pct*100}%"></div>`+
 TICKS.map(([o,l])=>{const p=pos(TARGET+o);if(p<0)return '';return `<div class="tl-tk${o==0?' tl-t tl-r':''}" style="left:${p}%" title="${l} · block ${fmtN(TARGET+o)}">${(o==0||100-p>9)?`<em>${l}</em>`:''}</div>`}).join('')+
 `<div class="tl-tk tl-l" style="left:0"><em>${fmtN(START)}</em></div><div class="tl-now" style="left:${c.pct*100}%" title="Block ${fmtN(tip)}"></div></div>`;}
function grid(c){return `<div class="tl-grid"><div><span>CURRENT BLOCK</span><b>${fmtN(tip)}</b></div><div><span>TARGET</span><b>${fmtN(TARGET)}</b></div><div><span>BLOCKS LEFT</span><b>${fmtN(c.left)}</b></div><div><span>EST. ARRIVAL (your time)</span><b style="font-size:15px">${c.eta.toLocaleString([],{weekday:'short',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit',hour12:false})}</b></div></div>`;}
let pill,ov,stk;
function render(){const c=calc();
 const head=c?(c.live?`<span class="tl-tag">$SHNAKAS</span><span class="tl-cd tl-live">REWARDS LIVE 🎉</span><span class="tl-sm">block ${fmtN(tip)} ≥ ${fmtN(TARGET)}</span>`
  :`<span class="tl-tag">$SHNAKAS REWARDS IN</span><span class="tl-cd">${cd(c.ms)}</span><span class="tl-mini"><b style="width:${c.pct*100}%"></b></span><span class="tl-sm">${fmtN(c.left)} blocks</span>`)
  :`<span class="tl-tag">$SHNAKAS REWARDS</span><span class="tl-sm">${err?'block height unavailable — retrying':'loading block height…'}</span>`;
 const body=c?`${grid(c)}${bar(c)}<div class="tl-sm">Block 971,700 = $SHNAKAS rewards start for unlisted Shielded Nakas. ETA uses avg block time ${(avg/60).toFixed(1)} min (mempool.space) — estimate only.</div>`:'';
 if(ov&&ov.classList.contains('tl-on')){ov.querySelector('.tl-row').innerHTML=head;ov.querySelector('.tl-exp').innerHTML=body;}
 if(pill){const m=c&&!c.live?Math.floor(c.ms/60000):0;pill.innerHTML=c?(c.live?'⏱ <b>$SHNAKAS</b> LIVE':`⏱ <b>$SHNAKAS</b> ${Math.floor(m/1440)}D ${String(Math.floor(m%1440/60)).padStart(2,'0')}H ${String(m%60).padStart(2,'0')}M`):'⏱ <b>$SHNAKAS</b> …';}
 if(stk)stk.innerHTML=c?(c.live?'REWARDS LIVE':`$SHNAKAS IN ${cd(c.ms).replace(/<i>(.)<\/i>/g,'$1 ').replace(/ \d+S $/,'')}<small>block ${fmtN(TARGET)} · ${fmtN(c.left)} left</small>`):'$SHNAKAS · BLOCK 971,700';}
function open(){ov.classList.add('tl-on');render();}
function close(){ov.classList.remove('tl-on');}
function init(){pill=document.createElement('button');pill.type='button';pill.className='tl-pill';pill.setAttribute('aria-label','$SHNAKAS rewards countdown');
 pill.onclick=e=>{e.stopPropagation();ov.classList.contains('tl-on')?close():open();};document.body.appendChild(pill);
 ov=document.createElement('div');ov.className='tl-ov';ov.innerHTML='<div class="tl-panel" role="dialog" aria-label="$SHNAKAS rewards timeline"><button class="tl-x" aria-label="Close">✕</button><div class="tl-row"></div><div class="tl-exp"></div></div>';
 ov.addEventListener('click',e=>{if(e.target===ov)close();});ov.querySelector('.tl-x').onclick=close;document.body.appendChild(ov);
 addEventListener('keydown',e=>{if(e.key=='Escape'&&ov.classList.contains('tl-on')){e.stopImmediatePropagation();close();}},true);
 const land=document.getElementById('land');if(land){stk=document.createElement('div');stk.className='tl-stk';land.appendChild(stk);}
 render();getTip().then(render);getAvg().then(render);setInterval(()=>getTip().then(render),60000);setInterval(render,1000);}
window.ShnakasTimeline={get tip(){return tip},calc,open,close};
if(document.readyState=='loading')document.addEventListener('DOMContentLoaded',init);else init();})();
