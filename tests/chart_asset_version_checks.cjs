/* Offline content-bound chart asset cache-key regression. */
const assert=require('node:assert/strict'),crypto=require('node:crypto'),fs=require('node:fs'),path=require('node:path');
const folder=path.join(__dirname,'../artifacts/daily-market-brief');
const html=fs.readFileSync(path.join(folder,'index.html'),'utf8'),asset=fs.readFileSync(path.join(folder,'tradingview.js'));
const digest=bytes=>crypto.createHash('sha256').update(bytes).digest('hex').slice(0,12);
function validate(page,bytes){
  const scripts=[...page.matchAll(/<script\b[^>]*\bsrc="([^"]+)"[^>]*><\/script>/g)];
  const local=scripts.filter(match=>match[1].split('?')[0]==='./tradingview.js');
  assert.equal(local.length,1,'Exactly one relative local chart script');
  assert.equal(local[0][1],'./tradingview.js?v='+digest(bytes),'Chart asset version must match current script bytes');
  const resolved=new URL(local[0][1],'https://example.invalid/praesagus/daily-market-brief/');
  assert.equal(resolved.pathname,'/praesagus/daily-market-brief/tradingview.js');
}
validate(html,asset);
const valid=html.replace(/src="\.\/tradingview\.js(?:\?[^"]*)?"/,'src="./tradingview.js?v='+digest(asset)+'"');
validate(valid,asset);
assert.throws(()=>validate(valid.replace('?v='+digest(asset),''),asset),/version must match/);
assert.throws(()=>validate(valid.replace('?v='+digest(asset),'?v=000000000000'),asset),/version must match/);
assert.throws(()=>validate(valid,Buffer.concat([asset,Buffer.from('\n// changed bytes')])),/version must match/);
assert.throws(()=>validate(valid.replace('./tradingview.js','/tradingview.js'),asset),/Exactly one relative/);
assert.throws(()=>validate(valid+'<script src="./tradingview.js?v='+digest(asset)+'"></script>',asset),/Exactly one relative/);
console.log('Chart asset version checks passed: SHA256 cache key, relative Pages path, missing/stale/changed-byte version and duplicate rejection. HTML caches and live delivery unverified.');
