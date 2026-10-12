// Flappy Nakas — standalone mini-game for The Vault (additive, scoped "fnk-" prefix)
(function(){
'use strict';
const css=`
.fnk-btn{position:fixed;right:12px;bottom:34px;z-index:6;font:18px Anton,Impact,sans-serif;letter-spacing:.04em;background:#f26a1b;color:#000;border:3px solid #000;border-radius:3px;padding:8px 14px;cursor:pointer;box-shadow:4px 4px 0 #000;transform:rotate(-2deg)}
.fnk-btn:hover{transform:rotate(-2deg) translate(-2px,-2px);box-shadow:6px 6px 0 #000}
#res[style*="block"]~.fnk-btn,#list[style*="block"]~.fnk-btn,body.landing .fnk-btn,html.mob .fnk-btn{display:none}
.fnk-ov{position:fixed;inset:0;z-index:100;background:rgba(0,0,0,.75);display:none;align-items:center;justify-content:center;padding:env(safe-area-inset-top) 8px env(safe-area-inset-bottom)}
.fnk-ov.fnk-on{display:flex}
.fnk-box{position:relative;background:#f26a1b radial-gradient(rgba(0,0,0,.18) 1.2px,transparent 1.6px) 0 0/7px 7px;border:4px solid #000;box-shadow:10px 10px 0 #000;padding:12px;width:min(520px,96vw);max-height:96vh;display:flex;flex-direction:column;gap:8px}
.fnk-hd{display:flex;justify-content:space-between;align-items:center}
.fnk-hd b{font:28px Anton,Impact,sans-serif;color:#000;letter-spacing:.03em}
.fnk-hd span{background:#000;color:#fff;font:15px Anton,Impact,sans-serif;padding:3px 10px;transform:rotate(-2deg);display:inline-block}
.fnk-x{font:20px Anton,Impact,sans-serif;background:#f3ead6;color:#000;border:3px solid #000;min-width:44px;min-height:44px;cursor:pointer;box-shadow:3px 3px 0 #000}
.fnk-cv{width:100%;display:block;border:3px solid #000;background:#0d0b09;touch-action:none;cursor:pointer;aspect-ratio:2/3;max-height:calc(96vh - 110px);object-fit:contain}
.fnk-ft{font:13px system-ui,sans-serif;font-weight:700;color:#000;text-align:center}
.fnk-wrap{position:relative}
.fnk-lb{position:absolute;left:6%;right:6%;top:45%;bottom:4%;display:none;flex-direction:column;gap:6px;background:rgba(13,11,9,.92);border:3px solid #000;box-shadow:4px 4px 0 #f26a1b;padding:8px;color:#f3ead6;font:12px system-ui,sans-serif;overflow:hidden}
.fnk-lb.fnk-on{display:flex}
.fnk-row{display:flex;gap:5px}
.fnk-row input{flex:1;min-width:0;font:14px system-ui,sans-serif;padding:6px;border:2px solid #000;background:#f3ead6;color:#000;border-radius:0}
.fnk-row button{font:14px Anton,Impact,sans-serif;letter-spacing:.03em;border:2px solid #000;background:#f26a1b;color:#000;padding:4px 9px;cursor:pointer;min-height:34px;white-space:nowrap}
.fnk-row button.fnk-sx{background:#f3ead6}
.fnk-row button:disabled{opacity:.5;cursor:default}
.fnk-msg{min-height:14px;font-weight:700;color:#f26a1b}
.fnk-tt{font:15px Anton,Impact,sans-serif;letter-spacing:.04em;color:#f26a1b}
.fnk-top{margin:0;padding:0;list-style:none;display:grid;grid-template-columns:1fr 1fr;grid-auto-flow:column;grid-template-rows:repeat(5,auto);gap:2px 10px;overflow:auto;min-height:0}
.fnk-top li{display:flex;justify-content:space-between;gap:4px;white-space:nowrap;overflow:hidden}
.fnk-top li span{overflow:hidden;text-overflow:ellipsis}
.fnk-top li b{color:#f26a1b}
.fnk-tap{margin-top:auto;text-align:center;font:13px Anton,Impact,sans-serif;letter-spacing:.04em;color:#f26a1b;cursor:pointer}
@media (max-width:420px){.fnk-lb{left:3%;right:3%;top:43%;padding:6px;font-size:11px}.fnk-row button{padding:4px 6px;font-size:13px}}`;
const st=document.createElement('style');st.textContent=css;document.head.appendChild(st);

const W=360,H=540; // logical size
let ov,cv,ctx,dpr=1,raf=0,last=0,running=false,state='ready',bird,pipes,score=0,best=+(localStorage.getItem('fnkBest')||0),t=0,img=null,imgOk=false,spawnT=0,playT=0,flaps=0,sent=false,lb=null,topList=[];
const G=1500,FLAP=-430,SPEED=150,GAP=150,PW=62,SPAWN=1.55;
const LB='https://nakas-flappy.shielded-vault.workers.dev',APP='https://3ajfr.github.io/shielded-nakas-dashboard/vault/';
const sfx=()=>{try{return window.VAULT&&window.VAULT.sfx}catch(e){return null}};
function snd(k){const s=sfx();if(!s)return;try{if(k=='flap')s.blip();else if(k=='score')s.clink(0);else if(k=='die')s.whoosh&&s.whoosh();}catch(e){}}

function loadImg(){const u=window.VAULT&&window.VAULT.prizeImg;if(!u)return;img=new Image();img.crossOrigin='anonymous';img.onload=()=>imgOk=true;img.onerror=()=>imgOk=false;img.src=u;}
function drawHoodie(x,y,s){ // fallback pixel-art red hoodie (12x12 grid)
 const P=['....RRRR....','..RRRRRRRR..','.RRRSSSSRRR.','.RRSSSSSSRR.','RRSWWWWWWSRR','RRSWBBBBWSRR','RRSSSSSSSSRR','RRSSSSSSSSRR','RRRSSSSSSRRR','RRRRWRRWRRRR','RRRRWRRWRRRR','RRRRRRRRRRRR'];
 const C={R:'#d81e1e',S:'#e8c39e',W:'#f3ead6',B:'#1d4ed8'},p=s/12;
 for(let j=0;j<12;j++)for(let i=0;i<12;i++){const c=C[P[j][i]];if(c){ctx.fillStyle=c;ctx.fillRect(x+i*p,y+j*p,p+.5,p+.5);}}}
function reset(){bird={x:96,y:H/2,v:0,r:19};pipes=[];score=0;spawnT=0;t=0;playT=0;flaps=0;sent=false;showLb(false);}
function flap(){if(state=='ready'){state='play';reset();bird.v=FLAP;flaps=1;snd('flap');return;}
 if(state=='play'){bird.v=FLAP;flaps++;snd('flap');return;}
 if(state=='over'&&t>.6){state='ready';reset();}}
function die(){if(state!='play')return;state='over';t=0;snd('die');if(score>best){best=score;localStorage.setItem('fnkBest',best);}showLb(true);}
function update(dt){t+=dt;if(state!='play'){if(state=='ready')bird.y=H/2+Math.sin(t*3)*8;return;}
 playT+=dt;bird.v+=G*dt;bird.y+=bird.v*dt;
 spawnT-=dt;if(spawnT<=0){spawnT=SPAWN;const gy=90+Math.random()*(H-180-GAP-40);pipes.push({x:W+10,gy,passed:false});}
 for(const p of pipes){p.x-=SPEED*dt;if(!p.passed&&p.x+PW<bird.x){p.passed=true;score++;snd('score');}
  const inX=bird.x+bird.r>p.x&&bird.x-bird.r<p.x+PW,inGap=bird.y-bird.r>p.gy&&bird.y+bird.r<p.gy+GAP;if(inX&&!inGap)die();}
 pipes=pipes.filter(p=>p.x>-PW-10);
 if(bird.y+bird.r>H-40||bird.y-bird.r<0)die();}
function pillar(x,y,h,top){ctx.fillStyle='#0d0b09';ctx.fillRect(x,y,PW,h);ctx.fillStyle='#f26a1b';
 for(let k=0;k<h;k+=26)ctx.fillRect(x+6,y+k+6,PW-12,12);ctx.fillStyle='#000';ctx.fillRect(x-6,top?y+h-18:y,PW+12,18);ctx.fillStyle='#f3ead6';ctx.fillRect(x-6,top?y+h-18:y,PW+12,4);
 ctx.strokeStyle='#000';ctx.lineWidth=3;ctx.strokeRect(x,y,PW,h);}
function txt(s,x,y,sz,col,al){ctx.font=`${sz}px Anton, Impact, sans-serif`;ctx.textAlign=al||'center';ctx.lineWidth=6;ctx.strokeStyle='#000';ctx.strokeText(s,x,y);ctx.fillStyle=col;ctx.fillText(s,x,y);}
function render(){ctx.setTransform(dpr*cv.width/(W*dpr),0,0,dpr*cv.height/(H*dpr),0,0);
 const g=ctx.createLinearGradient(0,0,0,H);g.addColorStop(0,'#1b0f07');g.addColorStop(1,'#0d0b09');ctx.fillStyle=g;ctx.fillRect(0,0,W,H);
 ctx.fillStyle='rgba(242,106,27,.08)';for(let i=0;i<W;i+=12)for(let j=(i/12%2)*6;j<H;j+=12)ctx.fillRect(i,j,2,2);
 for(const p of pipes){pillar(p.x,0,p.gy,true);pillar(p.x,p.gy+GAP,H-40-p.gy-GAP,false);}
 ctx.fillStyle='#f3ead6';ctx.fillRect(0,H-40,W,40);ctx.fillStyle='#000';ctx.fillRect(0,H-40,W,4);
 const off=(t*SPEED)%24;for(let i=-off;i<W;i+=24){ctx.fillStyle='#f26a1b';ctx.fillRect(i,H-30,12,8);}
 ctx.save();ctx.translate(bird.x,bird.y);ctx.rotate(Math.max(-.5,Math.min(1.1,bird.v/700)));const s=bird.r*2.4;
 if(imgOk){ctx.imageSmoothingEnabled=false;ctx.drawImage(img,-s/2,-s/2,s,s);ctx.strokeStyle='#000';ctx.lineWidth=3;ctx.strokeRect(-s/2,-s/2,s,s);}else drawHoodie(-s/2,-s/2,s);
 ctx.restore();
 if(state=='play')txt(String(score),W/2,70,54,'#f3ead6');
 if(state=='ready'){txt('FLAPPY NAKAS',W/2,140,46,'#f26a1b');txt('THE PRIZE #1052',W/2,180,22,'#f3ead6');txt('TAP · CLICK · SPACE',W/2,H-80,20,'#f3ead6');txt('BEST '+best,W/2,215,18,'#f26a1b');startBoard();}
 if(state=='over'){ctx.fillStyle='rgba(0,0,0,.55)';ctx.fillRect(0,0,W,H);txt('GAME OVER',W/2,105,48,'#d81e1e');txt('SCORE '+score,W/2,160,30,'#f3ead6');txt('BEST '+best,W/2,198,24,'#f26a1b');
  if(!lb||!lb.classList.contains('fnk-on')){txt('THE PRIZE #1052',W/2,320,20,'#f3ead6');if(t>.6)txt('TAP TO RETRY',W/2,H-80,22,'#f26a1b');}}}
function startBoard(){const x=40,y=298,w=W-80,n=Math.min(5,topList.length),h=n?50+n*17:70; // start-screen board (canvas only: never blocks taps)
 ctx.fillStyle='#f26a1b';ctx.fillRect(x+4,y+4,w,h);ctx.fillStyle='rgba(13,11,9,.94)';ctx.fillRect(x,y,w,h);ctx.strokeStyle='#000';ctx.lineWidth=3;ctx.strokeRect(x,y,w,h);
 txt('🏆 TOP PILOTS',W/2,y+22,17,'#f26a1b');
 if(!n){txt('Be the first on the board!',W/2,y+50,16,'#f3ead6');return;}
 const cut=s=>s.length>14?s.slice(0,13)+'…':s;
 for(let i=0;i<n;i++){const e=topList[i],yy=y+42+i*17;txt((i+1)+'. '+cut(String(e.name)),x+12,yy,14,i?'#f3ead6':'#f26a1b','left');txt(String(e.score),x+w-12,yy,14,i?'#f3ead6':'#f26a1b','right');}
 txt('BEAT #1: '+cut(String(topList[0].name))+' '+topList[0].score,W/2,y+h-7,13,'#f26a1b');}
// ---- global leaderboard (Cloudflare Worker; no secrets client-side; fails gracefully) ----
function req(path,opt){const c=new AbortController(),k=setTimeout(()=>c.abort(),6000);return fetch(LB+path,{...opt,signal:c.signal}).finally(()=>clearTimeout(k));}
function drawTop(){if(!lb)return;const ul=lb.querySelector('.fnk-top');ul.textContent='';
 if(!topList.length){const li=document.createElement('li');li.textContent='No scores yet — be first!';ul.appendChild(li);return;}
 topList.slice(0,10).forEach((e,i)=>{const li=document.createElement('li'),a=document.createElement('span'),b=document.createElement('b');a.textContent=(i+1)+'. '+e.name;b.textContent=e.score;li.append(a,b);ul.appendChild(li);});}
function loadTop(){req('/top').then(r=>r.ok?r.json():Promise.reject()).then(d=>{if(Array.isArray(d)){topList=d;drawTop();}}).catch(()=>{if(lb&&!topList.length){const ul=lb.querySelector('.fnk-top');ul.innerHTML='<li>Leaderboard offline</li>';}});}
function msg(m){if(lb)lb.querySelector('.fnk-msg').textContent=m;}
function submit(){const inp=lb.querySelector('input'),name=inp.value.trim().slice(0,16),btn=lb.querySelector('.fnk-sb');
 if(!name){msg('Enter a name');inp.focus();return;}if(score<1){msg('Score at least 1 to submit');return;}if(sent)return;
 try{localStorage.setItem('fnkName',name);}catch(e){}btn.disabled=true;msg('Sending…');
 req('/score',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,score,dur:Math.round(playT*1000),flaps})})
  .then(r=>r.json().then(d=>({ok:r.ok,d})))
  .then(({ok,d})=>{if(ok){sent=true;if(d.top){topList=d.top;drawTop();}msg(d.improved?('Saved! Rank #'+d.rank):'Your best ('+(d.rank?'#'+d.rank:'')+') is already higher');}
   else{btn.disabled=false;msg(d.error=='rate'?('Wait '+(d.retry||20)+'s and retry'):d.error=='implausible'?'Score rejected':'Error: '+(d.error||'try again'));}})
  .catch(()=>{btn.disabled=false;msg('Leaderboard unreachable — try later');});}
function share(){const tx='I scored '+score+' on Flappy Nakas 🎮 in The Vault by @ShieldedNakas. Can you beat me?';
 window.open('https://twitter.com/intent/tweet?text='+encodeURIComponent(tx)+'&url='+encodeURIComponent(APP),'_blank','noopener');}
function showLb(on){if(!lb)return;lb.classList.toggle('fnk-on',!!on);if(on){msg('');lb.querySelector('.fnk-sb').disabled=score<1;lb.querySelector('.fnk-sc').textContent=score;drawTop();loadTop();}}
function loop(ts){if(!running)return;const dt=Math.min(.033,(ts-(last||ts))/1000);last=ts;update(dt);render();raf=requestAnimationFrame(loop);}
function fit(){dpr=Math.min(window.devicePixelRatio||1,2.5);const r=cv.getBoundingClientRect();const w=Math.max(1,Math.round(r.width*dpr)),h=Math.max(1,Math.round(r.height*dpr));if(cv.width!=w||cv.height!=h){cv.width=w;cv.height=h;}}
function open(){if(!ov)build();ov.classList.add('fnk-on');loadTop();if(!img)loadImg();fit();if(!bird)reset();running=true;last=0;cancelAnimationFrame(raf);raf=requestAnimationFrame(loop);}
function close(){if(!ov)return;ov.classList.remove('fnk-on');running=false;cancelAnimationFrame(raf);if(state=='play'){state='ready';reset();}}
function build(){ov=document.createElement('div');ov.className='fnk-ov';ov.innerHTML='<div class="fnk-box" role="dialog" aria-label="Flappy Nakas"><div class="fnk-hd"><b>FLAPPY NAKAS</b><span>THE PRIZE #1052</span><button class="fnk-x" aria-label="Close">✕</button></div><div class="fnk-wrap"><canvas class="fnk-cv"></canvas><div class="fnk-lb"><div class="fnk-row"><input maxlength="16" placeholder="Your name" aria-label="Your name" autocomplete="nickname"><button class="fnk-sb" type="button">SUBMIT <span class="fnk-sc"></span></button><button class="fnk-sx" type="button" aria-label="Share on X">SHARE 𝕏</button></div><div class="fnk-msg"></div><div class="fnk-tt">🏆 GLOBAL TOP 10</div><ol class="fnk-top"></ol><div class="fnk-tap">TAP HERE TO RETRY</div></div></div><div class="fnk-ft">Tap / click / SPACE to flap · Esc to close</div></div>';
 document.body.appendChild(ov);cv=ov.querySelector('canvas');ctx=cv.getContext('2d');
 ov.querySelector('.fnk-x').onclick=e=>{e.stopPropagation();close();};
 ov.addEventListener('click',e=>{if(e.target===ov)close();});
 cv.addEventListener('pointerdown',e=>{e.preventDefault();e.stopPropagation();flap();});
 lb=ov.querySelector('.fnk-lb');try{lb.querySelector('input').value=localStorage.getItem('fnkName')||'';}catch(e){}
 lb.addEventListener('pointerdown',e=>e.stopPropagation());lb.addEventListener('click',e=>e.stopPropagation());
 lb.querySelector('.fnk-sb').onclick=submit;lb.querySelector('.fnk-sx').onclick=share;lb.querySelector('.fnk-tap').onclick=()=>{if(state=='over'){state='ready';reset();}};
 addEventListener('resize',()=>{if(running)fit();});}
addEventListener('keydown',e=>{if(!ov||!ov.classList.contains('fnk-on'))return;if(e.target&&e.target.tagName=='INPUT'&&e.key!='Escape'){e.stopPropagation();if(e.key=='Enter'){e.preventDefault();submit();}return;}if(e.key=='Escape'){e.stopImmediatePropagation();close();}else if(e.code=='Space'||e.key==' '||e.key=='ArrowUp'){e.preventDefault();e.stopImmediatePropagation();flap();}},true);
function init(){const b=document.createElement('button');b.className='fnk-btn';b.type='button';b.textContent='🎮 FLAPPY NAKAS';b.onclick=open;document.body.appendChild(b);
 const mm=document.getElementById('mmenu');if(mm){const m=document.createElement('button');m.type='button';m.className='dark';m.id='fnkMenu';m.textContent='🎮 Flappy Nakas';m.onclick=()=>{mm.classList.remove('on');open();};mm.appendChild(m);}}
window.FlappyNakas={open,close,get state(){return state},get score(){return score}};
if(document.readyState=='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
