// nakas-live: CORS-enabled, edge-cached mirror of PUBLIC Shielded feeds for The Vault.
// /listings = public shielded listings, /sales = public secondary-market trades.
// No API key anywhere, 0 Ord Dropz key units. Cached 60 s (listings) / 120 s (sales) at the edge.
// Deploy: cd live_worker && npx wrangler deploy  (Cloudflare Workers, no secrets needed)
const SRC='https://shielded-mint-server-production.up.railway.app/api/shielded/listings';
const SALES='https://backend-secondary-market-production.up.railway.app/api/secondary/trades/collection/shielded-nakas-mupv6wja';
const ORIGINS=['https://3ajfr.github.io'];
function cors(req){const o=req.headers.get('Origin')||'';const ok=ORIGINS.includes(o)||/^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(o);
 return ok?{'Access-Control-Allow-Origin':o,'Access-Control-Allow-Methods':'GET,OPTIONS','Access-Control-Max-Age':'86400','Vary':'Origin'}:{'Vary':'Origin'};}
async function build(){
 const r=await fetch(SRC,{headers:{'Accept':'application/json','User-Agent':'nakas-vault-live'},cf:{cacheTtl:0}});
 if(!r.ok)throw new Error('upstream '+r.status);
 let d=await r.json();if(!Array.isArray(d))d=d&&(d.data||d.listings);
 if(!Array.isArray(d)||!d.length)throw new Error('empty');
 // same filter as vault_build/build_vault_data.py
 const l=d.filter(x=>x&&x.inscriptionId&&!x.pending&&!x.cancelling&&+x.price>=1000).map(x=>[x.inscriptionId,+x.price]);
 if(!l.length)throw new Error('no usable listings');
 return {at:new Date().toISOString(),src:'public /api/shielded/listings',n:l.length,l};}
async function sales(){
 const r=await fetch(SALES,{headers:{'Accept':'application/json','User-Agent':'nakas-vault-live'}});
 if(!r.ok)throw new Error('upstream '+r.status);
 let d=await r.json();if(!Array.isArray(d))d=d&&(d.data||d.trades||d.items);
 if(!Array.isArray(d))throw new Error('bad payload');
 const seen=new Set(),s=[];
 for(const t of d){if(!t||t.status!=='completed'||!t.salePrice||!t.inscriptionId)continue;const k=t.id||(t.txId+'-'+t.inscriptionId);if(seen.has(k))continue;seen.add(k);
  s.push([t.inscriptionId,+t.salePrice,t.completedAt||t.createdAt,t.txId||'']);}
 s.sort((a,b)=>b[2].localeCompare(a[2]));
 return {at:new Date().toISOString(),src:'public secondary trades',n:s.length,s};}
const ROUTES={'/listings':[build,60],'/sales':[sales,120]};
export default{async fetch(req,env,ctx){
 const url=new URL(req.url),h=cors(req);
 if(req.method==='OPTIONS')return new Response(null,{status:h['Access-Control-Allow-Origin']?204:403,headers:h});
 const rt=ROUTES[url.pathname];
 if(!rt||req.method!=='GET')return new Response('not found',{status:404,headers:h});
 const cache=caches.default,ck=new Request('https://cache.local'+url.pathname);
 let res=await cache.match(ck);
 if(!res){try{const body=JSON.stringify(await rt[0]());
   res=new Response(body,{headers:{'Content-Type':'application/json','Cache-Control':'public, max-age='+rt[1]}});ctx.waitUntil(cache.put(ck,res.clone()));}
  catch(e){return new Response(JSON.stringify({error:String(e.message||e)}),{status:502,headers:{'Content-Type':'application/json','Cache-Control':'no-store',...h}});}}
 const out=new Response(res.body,res);out.headers.set('Cache-Control','no-store');for(const [k,v] of Object.entries(h))out.headers.set(k,v);return out;}};
