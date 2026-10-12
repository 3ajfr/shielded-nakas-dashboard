// $SHNAKAS rewards timeline (block 971,700) — additive module, scoped "tl-" CSS
(function(){'use strict';
const TARGET=971700,START=969000,TICKS=[[-1000,'-1000'],[-500,'-500'],[-144,'~1 DAY'],[-6,'~1 H'],[0,'REWARDS START']];
const css=`
.tl-strip{position:fixed;z-index:6;top:96px;left:492px;right:362px;min-width:300px;background:rgba(13,11,9,.92);border:2px solid #f26a1b;border-radius:4px;box-shadow:5px 5px 0 rgba(242,106,27,.35);color:#f3ead6;font:13px SG,system-ui,sans-serif;cursor:pointer;user-select:none}
body.landing .tl-strip,html.mob .tl-strip{display:none}
.tl-row{display:flex;align-items:center;gap:10px;padding:6px 10px;white-space:nowrap;overflow:hidden}
.tl-tag{background:#000;color:#f26a1b;font:15px Anton,Impact,sans-serif;letter-spacing:.04em;padding:2px 8px;border:1px solid #f26a1b;transform:rotate(-1.5deg)}
.tl-cd{font:20px Anton,Impact,sans-serif;letter-spacing:.03em;color:#fff}.tl-cd i{font-style:normal;color:#f26a1b;font-size:13px;margin:0 3px 0 1px}
.tl-mini{flex:1;min-width:60px;height:8px;background:#2a221b;border:1px solid #000;position:relative;overflow:hidden}.tl-mini b{position:absolute;left:0;top:0;bottom:0;background:linear-gradient(90deg,#f26a1b,#d81e1e)}
.tl-sm{color:#b8ab92;font-size:12px}
.tl-exp{display:none;padding:4px 12px 12px;border-top:2px dashed rgba(242,106,27,.5)}.tl-strip.tl-open .tl-exp{display:block}
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
@media(max-width:1180px){.tl-strip .tl-sm{display:none}}`;
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
let strip,stk,mob;
function render(){const c=calc();
 const head=c?(c.live?`<span class="tl-tag">$SHNAKAS</span><span class="tl-cd tl-live">REWARDS LIVE 🎉</span><span class="tl-sm">block ${fmtN(tip)} ≥ ${fmtN(TARGET)}</span>`
  :`<span class="tl-tag">$SHNAKAS REWARDS IN</span><span class="tl-cd">${cd(c.ms)}</span><span class="tl-mini"><b style="width:${c.pct*100}%"></b></span><span class="tl-sm">${fmtN(c.left)} blocks · ▾</span>`)
  :`<span class="tl-tag">$SHNAKAS REWARDS</span><span class="tl-sm">${err?'block height unavailable — retrying':'loading block height…'}</span>`;
 const body=c?`${grid(c)}${bar(c)}<div class="tl-sm">Block 971,700 = $SHNAKAS rewards start for unlisted Shielded Nakas. ETA uses avg block time ${(avg/60).toFixed(1)} min (mempool.space) — estimate only.</div>`:'';
 if(strip){strip.querySelector('.tl-row').innerHTML=head;strip.querySelector('.tl-exp').innerHTML=body;}
 if(stk)stk.innerHTML=c?(c.live?'REWARDS LIVE':`$SHNAKAS IN ${cd(c.ms).replace(/<i>(.)<\/i>/g,'$1 ').replace(/\d+S $/,'').replace(/ \d+S/,'')}<small>block ${fmtN(TARGET)} · ${fmtN(c.left)} left</small>`):'$SHNAKAS · BLOCK 971,700';
 if(mob)mob.innerHTML=`<div class="tl-row" style="padding:0;flex-wrap:wrap;white-space:normal">${head.replace(' · ▾','')}</div>${body}`;}
function ensureMob(){const m=document.getElementById('mkt');if(!m||!document.documentElement.classList.contains('mob')||!mob)return;if(m.firstChild!==mob)m.prepend(mob);}
function init(){strip=document.createElement('div');strip.className='tl-strip';strip.innerHTML='<div class="tl-row"></div><div class="tl-exp"></div>';strip.onclick=()=>strip.classList.toggle('tl-open');document.body.appendChild(strip);
 const land=document.getElementById('land');if(land){stk=document.createElement('div');stk.className='tl-stk';land.appendChild(stk);}
 mob=document.createElement('div');mob.className='tl-mob';const m=document.getElementById('mkt');if(m)new MutationObserver(ensureMob).observe(m,{childList:true});
 render();getTip().then(()=>{render();ensureMob();});getAvg().then(render);setInterval(()=>getTip().then(render),60000);setInterval(render,1000);setTimeout(ensureMob,1500);}
window.ShnakasTimeline={get tip(){return tip},calc};
if(document.readyState=='loading')document.addEventListener('DOMContentLoaded',init);else init();})();
