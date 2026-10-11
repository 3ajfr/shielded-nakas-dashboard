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
.fnk-ft{font:13px system-ui,sans-serif;font-weight:700;color:#000;text-align:center}`;
const st=document.createElement('style');st.textContent=css;document.head.appendChild(st);

const W=360,H=540; // logical size
let ov,cv,ctx,dpr=1,raf=0,last=0,running=false,state='ready',bird,pipes,score=0,best=+(localStorage.getItem('fnkBest')||0),t=0,img=null,imgOk=false,spawnT=0;
const G=1500,FLAP=-430,SPEED=150,GAP=150,PW=62,SPAWN=1.55;
const sfx=()=>{try{return window.VAULT&&window.VAULT.sfx}catch(e){return null}};
function snd(k){const s=sfx();if(!s)return;try{if(k=='flap')s.blip();else if(k=='score')s.clink(0);else if(k=='die')s.whoosh&&s.whoosh();}catch(e){}}

function loadImg(){const u=window.VAULT&&window.VAULT.prizeImg;if(!u)return;img=new Image();img.crossOrigin='anonymous';img.onload=()=>imgOk=true;img.onerror=()=>imgOk=false;img.src=u;}
function drawHoodie(x,y,s){ // fallback pixel-art red hoodie (12x12 grid)
 const P=['....RRRR....','..RRRRRRRR..','.RRRSSSSRRR.','.RRSSSSSSRR.','RRSWWWWWWSRR','RRSWBBBBWSRR','RRSSSSSSSSRR','RRSSSSSSSSRR','RRRSSSSSSRRR','RRRRWRRWRRRR','RRRRWRRWRRRR','RRRRRRRRRRRR'];
 const C={R:'#d81e1e',S:'#e8c39e',W:'#f3ead6',B:'#1d4ed8'},p=s/12;
 for(let j=0;j<12;j++)for(let i=0;i<12;i++){const c=C[P[j][i]];if(c){ctx.fillStyle=c;ctx.fillRect(x+i*p,y+j*p,p+.5,p+.5);}}}
function reset(){bird={x:96,y:H/2,v:0,r:19};pipes=[];score=0;spawnT=0;t=0;}
function flap(){if(state=='ready'){state='play';reset();bird.v=FLAP;snd('flap');return;}
 if(state=='play'){bird.v=FLAP;snd('flap');return;}
 if(state=='over'&&t>.6){state='ready';reset();}}
function die(){if(state!='play')return;state='over';t=0;snd('die');if(score>best){best=score;localStorage.setItem('fnkBest',best);}}
function update(dt){t+=dt;if(state!='play'){if(state=='ready')bird.y=H/2+Math.sin(t*3)*8;return;}
 bird.v+=G*dt;bird.y+=bird.v*dt;
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
 if(state=='ready'){txt('FLAPPY NAKAS',W/2,140,46,'#f26a1b');txt('THE PRIZE #1052',W/2,180,22,'#f3ead6');txt('TAP · CLICK · SPACE',W/2,H-80,20,'#f3ead6');txt('BEST '+best,W/2,215,18,'#f26a1b');}
 if(state=='over'){ctx.fillStyle='rgba(0,0,0,.55)';ctx.fillRect(0,0,W,H);txt('GAME OVER',W/2,170,52,'#d81e1e');txt('SCORE '+score,W/2,230,30,'#f3ead6');txt('BEST '+best,W/2,268,24,'#f26a1b');
  txt('THE PRIZE #1052',W/2,320,20,'#f3ead6');if(t>.6)txt('TAP TO RETRY',W/2,H-80,22,'#f26a1b');}}
function loop(ts){if(!running)return;const dt=Math.min(.033,(ts-(last||ts))/1000);last=ts;update(dt);render();raf=requestAnimationFrame(loop);}
function fit(){dpr=Math.min(window.devicePixelRatio||1,2.5);const r=cv.getBoundingClientRect();const w=Math.max(1,Math.round(r.width*dpr)),h=Math.max(1,Math.round(r.height*dpr));if(cv.width!=w||cv.height!=h){cv.width=w;cv.height=h;}}
function open(){if(!ov)build();ov.classList.add('fnk-on');if(!img)loadImg();fit();if(!bird)reset();running=true;last=0;cancelAnimationFrame(raf);raf=requestAnimationFrame(loop);}
function close(){if(!ov)return;ov.classList.remove('fnk-on');running=false;cancelAnimationFrame(raf);if(state=='play'){state='ready';reset();}}
function build(){ov=document.createElement('div');ov.className='fnk-ov';ov.innerHTML='<div class="fnk-box" role="dialog" aria-label="Flappy Nakas"><div class="fnk-hd"><b>FLAPPY NAKAS</b><span>THE PRIZE #1052</span><button class="fnk-x" aria-label="Close">✕</button></div><canvas class="fnk-cv"></canvas><div class="fnk-ft">Tap / click / SPACE to flap · Esc to close</div></div>';
 document.body.appendChild(ov);cv=ov.querySelector('canvas');ctx=cv.getContext('2d');
 ov.querySelector('.fnk-x').onclick=e=>{e.stopPropagation();close();};
 ov.addEventListener('click',e=>{if(e.target===ov)close();});
 cv.addEventListener('pointerdown',e=>{e.preventDefault();e.stopPropagation();flap();});
 addEventListener('resize',()=>{if(running)fit();});}
addEventListener('keydown',e=>{if(!ov||!ov.classList.contains('fnk-on'))return;if(e.key=='Escape'){e.stopImmediatePropagation();close();}else if(e.code=='Space'||e.key==' '||e.key=='ArrowUp'){e.preventDefault();e.stopImmediatePropagation();flap();}},true);
function init(){const b=document.createElement('button');b.className='fnk-btn';b.type='button';b.textContent='🎮 FLAPPY NAKAS';b.onclick=open;document.body.appendChild(b);
 const mm=document.getElementById('mmenu');if(mm){const m=document.createElement('button');m.type='button';m.className='dark';m.id='fnkMenu';m.textContent='🎮 Flappy Nakas';m.onclick=()=>{mm.classList.remove('on');open();};mm.appendChild(m);}}
window.FlappyNakas={open,close,get state(){return state},get score(){return score}};
if(document.readyState=='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
