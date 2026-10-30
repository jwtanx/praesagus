/* Offline real-DOM tests. Existing isolated jsdom dependency; no external scripts loaded. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),{spawnSync}=require('node:child_process');
const {JSDOM,VirtualConsole}=require(path.join(process.env.DAILY_REPORT_TEST_DEPS||'/tmp/praesagus-viewer-test-deps','node_modules/jsdom'));
const root=path.resolve(__dirname,'..'),moduleCode=fs.readFileSync(path.join(root,'artifacts/daily-market-brief/tradingview.js'),'utf8'),html=fs.readFileSync(path.join(root,'artifacts/daily-market-brief/index.html'),'utf8');
const localModuleTags=[...html.matchAll(/<script src="(\.\/tradingview\.js\?v=[a-f0-9]{12})"><\/script>/g)];
assert.equal(localModuleTags.length,1,'Exactly one versioned local chart module is injected');
const localModuleTag=localModuleTags[0][0];
const report=date=>JSON.parse(fs.readFileSync(path.join(root,'artifacts/daily-market-brief',date+'.json'),'utf8'));
const index=JSON.parse(fs.readFileSync(path.join(root,'artifacts/daily-market-brief/reports.json'),'utf8'));
async function settle(){for(let i=0;i<8;i++)await new Promise(resolve=>setImmediate(resolve))}
function mount({width=390,reduce=false,moduleMissing=false}={}){
  const routes={'./reports.json':index,'./2026-09-30.json':report('2026-09-30'),'./2026-10-01.json':report('2026-10-01'),'../financial-calendar/2026-10.json':JSON.parse(fs.readFileSync(path.join(root,'artifacts/financial-calendar/2026-10.json'),'utf8'))};
  const requests=[],errors=[],timers=new Map(),idleTimers=new Map(),scrolls=[],frames=new Map(),visibility=[];let timerID=10000,frameID=0;let media;
  const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e));
  const dom=new JSDOM(moduleMissing?html:html.replace(localModuleTag,()=>'<script>'+moduleCode+'</script>'),{url:'https://example.org/praesagus/daily-market-brief/?view=technical&date=2026-10-01',runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,beforeParse(w){
    Object.defineProperty(w,'innerWidth',{value:width});media=new w.EventTarget();media.matches=reduce;w.matchMedia=()=>media;w.requestAnimationFrame=fn=>{const id=++frameID;frames.set(id,fn);return id};w.cancelAnimationFrame=id=>frames.delete(id);w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=function(options){scrolls.push(options)};w.IntersectionObserver=class{constructor(fn){this.fn=fn;this.disconnected=false;visibility.push(this)}observe(){this.fn([{isIntersecting:true}])}disconnect(){this.disconnected=true}};
    const originalTimeout=w.setTimeout.bind(w),originalClear=w.clearTimeout.bind(w);w.setTimeout=(fn,delay,...args)=>{if(delay===5000){const id=++timerID;idleTimers.set(id,fn);return id}if(delay===15000){const id=++timerID;timers.set(id,fn);return id}return originalTimeout(fn,delay,...args)};w.clearTimeout=id=>{if(idleTimers.has(id))idleTimers.delete(id);else if(timers.has(id))timers.delete(id);else originalClear(id)};
    w.fetch=async(url,options)=>{requests.push({url,options});const result=routes[url];if(result==='defer')return new Promise(resolve=>routes[url]={resolve});if(result instanceof Error)throw result;return {ok:!!result,status:result?200:404,json:async()=>JSON.parse(JSON.stringify(result))}}
  }});
  const $=selector=>dom.window.document.querySelector(selector);
  return {dom,w:dom.window,$,routes,requests,errors,timers,idleTimers,expireIdle(){for(const [id,fn] of [...idleTimers]){idleTimers.delete(id);fn()}},scrolls,frames,visibility,media,step(time){const scheduled=[...frames];for(const [id,fn] of scheduled){frames.delete(id);fn(time)}}};
}

function commit(t,ticker){const choice=t.$('#ta-candidate'),option=[...choice.options].find(o=>o.textContent.includes(' · '+ticker+' —')||o.textContent.endsWith(' · '+ticker));assert.ok(option,ticker);choice.value=option.value;choice.dispatchEvent(new t.w.Event('change',{bubbles:true}));t.$('#ta-show').click()}
async function identities(){
  const expectedUS={SPY:'AMEX:SPY',IWM:'AMEX:IWM',QQQ:'NASDAQ:QQQ',AAPL:'NASDAQ:AAPL',MSFT:'NASDAQ:MSFT',
    GOOGL:'NASDAQ:GOOGL',NVDA:'NASDAQ:NVDA',AVGO:'NASDAQ:AVGO',WMT:'NASDAQ:WMT',TSLA:'NASDAQ:TSLA',LIN:'NASDAQ:LIN',
    JPM:'NYSE:JPM',GS:'NYSE:GS',V:'NYSE:V',TSM:'NYSE:TSM',LLY:'NYSE:LLY',JNJ:'NYSE:JNJ',ABT:'NYSE:ABT',PG:'NYSE:PG',
    KO:'NYSE:KO',HD:'NYSE:HD',MCD:'NYSE:MCD',XOM:'NYSE:XOM',COP:'NYSE:COP',SLB:'NYSE:SLB',CAT:'NYSE:CAT',GE:'NYSE:GE',UPS:'NYSE:UPS',FCX:'NYSE:FCX',NEM:'NYSE:NEM'};
  const expectedMY={'0820EA':'MYX:F4GBM-EA','0800EA':'MYX:ABFMY1','1155':'MYX:MAYBANK','1023':'MYX:CIMB',
    '0277':'MYX:CLOUDPT','0259':'MYX:SNS','0166':'MYX:INARI','0097':'MYX:VITROX','5225':'MYX:IHH','5878':'MYX:KPJ',
    '4707':'MYX:NESTLE','3689':'MYX:F&N','5296':'MYX:MRDIY','4715':'MYX:GENM','6033':'MYX:PETGAS','5681':'MYX:PETDAG',
    '5246':'MYX:WPRTS','3816':'MYX:MISC','1961':'MYX:IOICORP','5285':'MYX:SDG'};

  const universe=JSON.parse(fs.readFileSync(path.join(root,'artifacts/daily-market-brief/watchlist-universe-five.json'),'utf8'));
  const rows=universe.groups.flatMap(g=>g.instruments);assert.equal(rows.length,50);
  const t=mount();await settle();
  for(const row of rows){const expected=(row.market==='US'?expectedUS:expectedMY)[row.ticker];assert.ok(expected);assert.equal(t.w.PraesagusTA.symbol(row),expected);assert.equal(t.w.PraesagusTA.external(row),'https://www.tradingview.com/chart/?symbol='+encodeURIComponent(expected));commit(t,row.ticker);const script=t.$('#ta-chart script');assert.equal(JSON.parse(script.textContent).symbol,expected);assert.equal(t.$('#ta-external').href,t.w.PraesagusTA.external(row));assert.match(t.$('#ta-status').textContent,/availability is unverified/);assert.ok(t.$('.tradingview-widget-copyright a'));}
  commit(t,'3689');assert.match(t.$('#ta-external').href,/symbol=MYX%3AF%26N$/);assert.doesNotMatch(t.$('#ta-external').href,/%253A|%2526/);
  for(const row of [{market:'US',ticker:'UNKNOWN'},{market:'US',ticker:'__proto__'},{market:'MY',ticker:'9999'},{market:'MY',ticker:'F&N'},{market:'MY',ticker:'SPY'},{market:'UK',ticker:'AAPL'},null]){assert.equal(t.w.PraesagusTA.symbol(row),null);assert.equal(t.w.PraesagusTA.external(row),'https://www.tradingview.com/symbols/');}
  assert.equal(t.errors.length,0);t.w.eval('ta.destroy()');t.w.close();
}
async function lifecycle(){
  const t=mount();await settle();assert.match(t.$('#ta-caption').textContent,/current or delayed, not frozen/);
  const script=t.$('#ta-chart script'),config=JSON.parse(script.textContent);assert.equal(config.symbol,'AMEX:SPY');assert.equal(config.allow_symbol_change,false);assert.equal(config.interval,'D');assert.equal(config.support_host,'https://www.tradingview.com');assert.equal('date' in config,false);assert.equal('forecasts' in config,false);
  assert.equal(t.$('#ta-external').rel,'noopener noreferrer');commit(t,'AAPL');const current=t.$('#ta-chart script');script.onerror();assert.equal(t.$('#ta-chart script'),current,'Stale error ignored');
  const frame=t.w.document.createElement('iframe');current.parentNode.querySelector('.tradingview-widget-container__widget').append(frame);await settle();assert.match(frame.title,/AAPL/);assert.match(t.$('#ta-status').textContent,/Data availability\/delay remains unverified/);assert.equal(t.timers.size,0);
  current.onerror();assert.equal(t.$('#ta-chart').children.length,0);assert.match(t.$('#ta-status').textContent,/unavailable or blocked/);assert.equal(t.$('#ta-external').hidden,false);
  commit(t,'AAPL');[...t.timers.values()][0]();assert.match(t.$('#ta-status').textContent,/unavailable or blocked/);assert.equal(t.timers.size,0);
  commit(t,'AAPL');t.$('[data-view="brief"]').click();assert.equal(t.$('#ta-chart').children.length,0);t.$('[data-view="technical"]').click();assert.equal(JSON.parse(t.$('#ta-chart script').textContent).symbol,'NASDAQ:AAPL');
  const controller=t.w.eval('ta');controller.update({forecasts:[{market:'US',ticker:'UNKNOWN',name:'Unknown'}]});assert.equal(t.$('#ta-chart').children.length,0);assert.equal(t.$('#ta-external').href,'https://www.tradingview.com/symbols/');assert.match(t.$('#ta-status').textContent,/No curated/);
  controller.update({forecasts:[{market:'MY',ticker:'9999',name:'Unknown'}]});assert.match(t.$('#ta-status').textContent,/No curated Bursa/);controller.destroy();assert.equal(t.timers.size,0);assert.equal(t.frames.size,0);assert.equal(t.idleTimers.size,0);assert.equal(t.errors.length,0);t.w.close();
}
async function datesAndSafety(){
  const t=mount({reduce:true});await settle();t.routes['./2026-09-30.json']='defer';const older=t.w.chooseReportDate('2026-09-30');await settle();assert.equal(t.$('#ta-candidate').options.length,1);assert.equal(t.$('#ta-chart').children.length,0);const resolve=t.routes['./2026-09-30.json'].resolve;
  await t.w.chooseReportDate('2026-10-01');await settle();resolve({ok:true,json:async()=>report('2026-09-30')});await older;await settle();assert.match(t.$('#ta-caption').textContent,/2026-10-01/);assert.match(t.$('#ta-selected').textContent,/SPY/);
  t.routes['./2026-09-30.json']=report('2026-09-30');await t.w.chooseReportDate('2026-09-30');await settle();commit(t,'AAPL');assert.match(t.$('#ta-evidence').textContent,/recorded forecast: up/);assert.match(t.$('#ta-caption').textContent,/2026-09-30/);
  t.routes['./2026-10-01.json']=new Error('offline error');await t.w.chooseReportDate('2026-10-01');await settle();assert.equal(t.$('#ta-candidate').options.length,1);assert.equal(t.$('#ta-chart').children.length,0);assert.match(t.$('#ta-status').textContent,/Watchlist unavailable/);
  const empty=report('2026-10-01');empty.forecasts=[];t.routes['./2026-10-01.json']=empty;await t.w.chooseReportDate('2026-10-01');await settle();assert.match(t.$('#ta-status').textContent,/No supported tickers/);
  t.w.eval('ta').update({metadata:{date:'<img src=x>'},forecasts:[{ticker:'<img>',market:'US'},{ticker:'javascript:evil',market:'US'},{ticker:'AAPL',name:'<img src=x>',market:'US',direction:'__proto__'},{ticker:'AAPL',market:'US'},{ticker:'1155',market:'MY'}]});assert.equal(t.$('#ta-candidate').options.length,3);assert.equal(t.$('#technical-view img'),null);assert.match(t.$('#ta-evidence').textContent,/recorded forecast: Unrated/);assert.equal(t.frames.size,0);assert.equal(t.idleTimers.size,0);assert.equal(t.$('#ta-motion-instruction'),null);assert.equal(t.$('#ta-chips').hasAttribute('tabindex'),false);assert.equal(t.$('#ta-chips').hasAttribute('aria-keyshortcuts'),false);
  for(const id of ['ta-search','ta-clear','ta-candidate','ta-show'])assert.equal(t.w.getComputedStyle(t.$('#'+id)).minHeight,'44px');
  t.w.eval('ta.destroy()');assert.equal(t.errors.length,0);t.w.close();
  const missing=mount({moduleMissing:true});await settle();assert.match(missing.$('#ta-status').textContent,/module cannot load/);assert.equal(missing.$('#ta-external').hidden,false);assert.equal(missing.errors.length,0);missing.w.close();
}
(async()=>{await identities();await lifecycle();await datesAndSafety();const replay=spawnSync(process.execPath,[path.join(root,'tests/daily_report_viewer_checks.cjs')],{cwd:root,encoding:'utf8'});assert.equal(replay.status,0,replay.stdout+replay.stderr);console.log('TradingView offline DOM checks passed: all50curated identities/once-encoded aliases, mapped/unmapped fallback, stale error/date cancellation, frame-vs-data distinction, attribution, 15sec timeout, inactive view/destroy, static native44px controls, safe content and complete daily viewer replay. No external scripts/network loaded.');})().catch(error=>{console.error(error);process.exitCode=1});
