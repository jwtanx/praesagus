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
async function directionsMappingAndLifecycle(){
  const t=mount({width:1280});await settle();
  assert.equal(t.$('#technical-view').classList.contains('hidden'),false);
  assert.match(t.$('#ta-caption').textContent,/2026-10-01/);assert.match(t.$('#ta-caption').textContent,/current or delayed, not frozen/);
  const script=t.$('#ta-chart script');assert.equal(script.src,'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js');const config=JSON.parse(script.textContent);assert.equal(config.symbol,'AMEX:SPY');assert.equal(config.allow_symbol_change,false);assert.equal(config.support_host,'https://www.tradingview.com');assert.equal(config.interval,'D');assert.equal('date' in config,false);assert.equal('forecasts' in config,false);
  assert.equal(t.$('#ta-external').hidden,false);assert.equal(t.$('#ta-external').rel,'noopener noreferrer');assert.ok(t.$('#ta-chart .tradingview-widget-copyright a'));
  assert.equal(t.w.PraesagusTA.symbol({market:'US',ticker:'AAPL'}),'NASDAQ:AAPL');assert.equal(t.w.PraesagusTA.symbol({market:'US',ticker:'UNKNOWN'}),null);assert.equal(t.w.PraesagusTA.symbol({market:'US',ticker:'__proto__'}),null);assert.equal(t.w.PraesagusTA.symbol({market:'MY',ticker:'AAPL'}),null);
  const first=t.$('#ta-chips button');assert.equal(first.textContent,'❔ SPY');assert.match(first.getAttribute('aria-label'),/SPY · Unrated report scenario/);assert.match(first.title,/Unrated recorded report scenario/);assert.equal(first.getAttribute('aria-pressed'),'true');
  const aapl=[...t.$('#ta-chips').children].find(b=>b.textContent.includes('AAPL'));aapl.click();assert.equal(JSON.parse(t.$('#ta-chart script').textContent).symbol,'NASDAQ:AAPL');assert.equal(script.isConnected,false);
  const current=t.$('#ta-chart script');script.onerror();assert.equal(current.isConnected,true,'Stale error cannot clear current widget');
  const frame=t.w.document.createElement('iframe');current.parentNode.querySelector('.tradingview-widget-container__widget').append(frame);await settle();assert.match(frame.title,/AAPL/);assert.match(t.$('#ta-status').textContent,/Data availability\/delay/);assert.equal(t.timers.size,0);
  const my=[...t.$('#ta-chips').children].find(b=>b.textContent.includes('0820EA'));my.click();assert.equal(JSON.parse(t.$('#ta-chart script').textContent).symbol,'MYX:F4GBM-EA');assert.match(t.$('#ta-status').textContent,/availability is unverified/);assert.match(t.$('#ta-external').href,/MYX%3AF4GBM-EA/);
  const gs=[...t.$('#ta-chips').children].find(b=>b.textContent==='📉 GS'||b.textContent==='❔ GS'||b.textContent==='📈 GS');gs.click();assert.equal(JSON.parse(t.$('#ta-chart script').textContent).symbol,'NYSE:GS');assert.match(t.$('#ta-external').href,/NYSE%3AGS/);
  aapl.click();const failed=t.$('#ta-chart script');failed.onerror();assert.equal(t.$('#ta-chart').children.length,0);assert.match(t.$('#ta-status').textContent,/unavailable or blocked/);assert.equal(t.$('#ta-external').hidden,false);
  aapl.click();const timeout=[...t.timers.values()][0];timeout();assert.match(t.$('#ta-status').textContent,/unavailable or blocked/);assert.equal(t.timers.size,0);
  aapl.click();t.$('.nav-link[data-view="brief"]').click();assert.equal(t.$('#ta-chart').children.length,0);assert.equal(t.timers.size,0);t.$('.nav-link[data-view="technical"]').click();assert.equal(t.$('#ta-chart script')!==null,true);
  assert.equal(t.errors.length,0);t.dom.window.close();
}
async function dateRacesAndErrors(){
  const t=mount();await settle();
  t.routes['./2026-09-30.json']='defer';const older=t.w.chooseReportDate('2026-09-30');await settle();assert.equal(t.$('#ta-chips').children.length,0);assert.equal(t.$('#ta-chart').children.length,0);
  const resolve=t.routes['./2026-09-30.json'].resolve;
  await t.w.chooseReportDate('2026-10-01');await settle();resolve({ok:true,json:async()=>report('2026-09-30')});await older;await settle();assert.match(t.$('#ta-caption').textContent,/2026-10-01/);assert.match(t.$('#ta-chips').textContent,/SPY/);
  t.routes['./2026-09-30.json']=report('2026-09-30');await t.w.chooseReportDate('2026-09-30');await settle();assert.match(t.$('#ta-caption').textContent,/2026-09-30/);assert.ok(t.$('#ta-chips .ta-up'));assert.ok(t.$('#ta-chips .ta-down'));assert.ok(t.$('#ta-chips .ta-flat'));assert.equal(t.$('#ta-chips .ta-up').tagName,'BUTTON');
  t.routes['./2026-10-01.json']=new Error('synthetic network failure');await t.w.chooseReportDate('2026-10-01');await settle();assert.equal(t.$('#ta-chips').children.length,0);assert.equal(t.$('#ta-chart').children.length,0);assert.match(t.$('#ta-status').textContent,/Watchlist unavailable/);assert.equal(t.timers.size,0);
  const missing=report('2026-10-01');missing.forecasts=[];t.routes['./2026-10-01.json']=missing;await t.w.chooseReportDate('2026-10-01');await settle();assert.match(t.$('#ta-status').textContent,/No supported tickers/);assert.equal(t.errors.length,0);t.dom.window.close();
}
async function keyboardSafetyAndMotion(){
  const t=mount({reduce:true,width:390});await settle();const first=t.$('#ta-chips button');first.focus();first.dispatchEvent(new t.w.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));assert.equal(t.w.document.activeElement,t.$('#ta-chips').children[1]);assert.equal(t.scrolls.at(-1).behavior,'auto');t.w.document.activeElement.dispatchEvent(new t.w.KeyboardEvent('keydown',{key:'End',bubbles:true}));assert.equal(t.w.document.activeElement,t.$('#ta-chips').lastChild);
  assert.equal(t.w.getComputedStyle(t.$('#ta-chips')).overflowX,'auto');assert.equal(t.w.getComputedStyle(first).minHeight,'44px');assert.equal(t.w.getComputedStyle(first).minWidth,'44px');assert.equal(t.w.getComputedStyle(first).padding,'2px');assert.equal(t.w.getComputedStyle(t.$('#ta-chips')).gap,'4px');assert.equal(t.w.getComputedStyle(t.$('#ta-caption')).margin,'4px 0px');assert.equal(t.$('#ta-motion'),null);assert.equal(t.w.getComputedStyle(first.querySelector('span')).fontSize,'12px');assert.equal(t.w.getComputedStyle(first.querySelector('span')).padding,'4px 8px');assert.equal(t.w.getComputedStyle(first.querySelector('span')).borderRadius,'999px');assert.match(html,/@media\(prefers-reduced-motion:reduce\)/);
  t.$('.nav-link[data-view="brief"]').click();const controller=t.w.PraesagusTA.create(t.$('#technical-view'));controller.show(true);controller.update({metadata:{date:'<img src=x>'},forecasts:[{ticker:'<img src=x>',market:'US'},{ticker:'javascript:evil',market:'US'},{ticker:'AAPL',market:'US',direction:'__proto__'},{ticker:'AAPL',market:'US',direction:'up'},{ticker:'1155',market:'MY',direction:'down'}]});assert.equal(t.$('#ta-chips').children.length,2);assert.equal(t.$('#ta-chips button').textContent,'❔ AAPL');assert.match(t.$('#ta-chips button').getAttribute('aria-label'),/Unrated report scenario/);assert.equal(t.$('#technical-view img'),null);assert.equal(t.$('#technical-view').querySelectorAll('script').length,1);controller.destroy();t.dom.window.close();
  const missing=mount({moduleMissing:true});await settle();assert.match(missing.$('#ta-status').textContent,/module cannot load/);assert.equal(missing.$('#ta-external').hidden,false);assert.equal(missing.errors.length,0);missing.dom.window.close();
}
async function deterministicTickerMotion(){
  const t=mount();await settle();
  const chips=t.$('#ta-chips');assert.equal(chips.tabIndex,0);assert.equal(chips.getAttribute('aria-keyshortcuts'),'Escape');assert.match(t.$('#ta-motion-instruction').textContent,/Escape.*stop motion for this session/);
  Object.defineProperty(chips,'scrollWidth',{configurable:true,value:700});
  Object.defineProperty(chips,'clientWidth',{configurable:true,value:300});
  t.w.dispatchEvent(new t.w.Event('resize'));assert.equal(t.frames.size,1);
  t.step(0);t.step(16);const firstStep=chips.scrollLeft;assert.ok(firstStep>0&&firstStep<1);
  t.step(32);assert.ok(chips.scrollLeft>firstStep);assert.equal(t.frames.size,1,'one animation frame');
  chips.dispatchEvent(new t.w.MouseEvent('mouseenter'));assert.equal(t.frames.size,0);const frozen=chips.scrollLeft;t.step(2000);assert.equal(chips.scrollLeft,frozen);
  chips.dispatchEvent(new t.w.MouseEvent('mouseleave'));assert.equal(t.frames.size,1);
  chips.firstChild.focus();assert.equal(t.frames.size,0);chips.firstChild.blur();assert.equal(t.frames.size,1);
  for(const type of ['wheel','touchmove','keydown']){chips.dispatchEvent(new t.w.Event(type,{bubbles:true}));assert.equal(t.frames.size,0);assert.equal(t.idleTimers.size,1);chips.dispatchEvent(new t.w.Event(type,{bubbles:true}));assert.equal(t.idleTimers.size,1,'one resettable idle timer');t.expireIdle();assert.equal(t.frames.size,1)}
  chips.dispatchEvent(new t.w.Event('wheel'));chips.dispatchEvent(new t.w.MouseEvent('mouseenter'));t.expireIdle();assert.equal(t.frames.size,0,'idle expiration cannot override hover');chips.dispatchEvent(new t.w.MouseEvent('mouseleave'));assert.equal(t.frames.size,1);
  chips.dispatchEvent(new t.w.Event('wheel'));chips.firstChild.focus();t.expireIdle();assert.equal(t.frames.size,0,'idle expiration cannot override focus');chips.firstChild.blur();assert.equal(t.frames.size,1);
  chips.dispatchEvent(new t.w.Event('wheel'));chips.scrollLeft=200;t.expireIdle();t.step(1000);assert.equal(chips.scrollLeft,200);t.step(1016);assert.ok(chips.scrollLeft>200&&chips.scrollLeft<201);
  Object.defineProperty(t.w.document,'hidden',{configurable:true,value:true});t.w.document.dispatchEvent(new t.w.Event('visibilitychange'));assert.equal(t.frames.size,0);
  Object.defineProperty(t.w.document,'hidden',{configurable:true,value:false});t.w.document.dispatchEvent(new t.w.Event('visibilitychange'));assert.equal(t.frames.size,1);
  const io=t.visibility[0];io.fn([{isIntersecting:false}]);assert.equal(t.frames.size,0);io.fn([{isIntersecting:true}]);assert.equal(t.frames.size,1);
  t.media.matches=true;t.media.dispatchEvent(new t.w.Event('change'));assert.equal(t.frames.size,0);
  t.media.matches=false;t.media.dispatchEvent(new t.w.Event('change'));assert.equal(t.frames.size,1);
  t.$('.nav-link[data-view="brief"]').click();assert.equal(t.frames.size,0);t.$('.nav-link[data-view="technical"]').click();assert.equal(t.frames.size,1);
  chips.dispatchEvent(new t.w.MouseEvent('mouseenter'));await t.w.chooseReportDate('2026-09-30');await settle();assert.equal(t.frames.size,0,'date update retains hover pause');chips.dispatchEvent(new t.w.MouseEvent('mouseleave'));assert.equal(t.frames.size,1);assert.equal(chips.scrollLeft,0);
  // Traverse a complete cosine cycle: smooth reversal, bounded steps, no wrap.
  let previous=0,previousDelta=0,reversed=false,maxDelta=0;
  for(let time=0;time<110000;time+=16){t.step(time);const position=chips.scrollLeft,delta=position-previous;assert.ok(position>=0&&position<=400);maxDelta=Math.max(maxDelta,Math.abs(delta));if(previousDelta>0&&delta<0){reversed=true;assert.ok(Math.abs(previousDelta)<0.01&&Math.abs(delta)<0.01)}previous=position;previousDelta=delta}
  assert.ok(reversed);assert.ok(maxDelta<0.2,'maximum speed approximately 12 pixels/sec');assert.equal(t.frames.size,1);
  Object.defineProperty(chips,'scrollWidth',{configurable:true,value:300});t.w.dispatchEvent(new t.w.Event('resize'));assert.equal(t.frames.size,0,'no overflow, no animation');
  // Escape is a persistent stop, even after idle/date/view/preference changes.
  Object.defineProperty(chips,'scrollWidth',{configurable:true,value:700});t.w.dispatchEvent(new t.w.Event('resize'));chips.focus();chips.dispatchEvent(new t.w.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));chips.blur();t.expireIdle();assert.equal(t.frames.size,0);
  chips.dispatchEvent(new t.w.Event('wheel'));assert.equal(t.idleTimers.size,0);await t.w.chooseReportDate('2026-10-01');await settle();t.$('.nav-link[data-view="brief"]').click();t.$('.nav-link[data-view="technical"]').click();t.w.dispatchEvent(new t.w.Event('resize'));assert.equal(t.frames.size,0,'Escape stop survives date/view changes');
  t.w.eval('ta.destroy()');assert.equal(io.disconnected,true);t.w.dispatchEvent(new t.w.Event('resize'));assert.equal(t.frames.size,0);assert.equal(t.idleTimers.size,0);assert.equal(t.timers.size,0);assert.equal(t.errors.length,0);t.w.close();
  const cleanup=mount();await settle();cleanup.$('#ta-chips').dispatchEvent(new cleanup.w.Event('wheel'));assert.equal(cleanup.idleTimers.size,1);await cleanup.w.chooseReportDate('2026-09-30');await settle();assert.equal(cleanup.idleTimers.size,0,'date update clears idle timer');cleanup.$('#ta-chips').dispatchEvent(new cleanup.w.Event('wheel'));cleanup.w.eval('ta.destroy()');assert.equal(cleanup.idleTimers.size,0,'destroy clears idle timer');cleanup.w.close();
  const reduced=mount({reduce:true});await settle();assert.equal(reduced.frames.size,0);assert.equal(reduced.$('#ta-motion'),null);reduced.w.close();
}
async function heldContacts(){
  const t=mount();await settle();const chips=t.$('#ta-chips');
  Object.defineProperty(chips,'scrollWidth',{value:700});Object.defineProperty(chips,'clientWidth',{value:300});t.w.dispatchEvent(new t.w.Event('resize'));
  function event(target,type,details={}){const e=new t.w.Event(type,{bubbles:true});for(const [key,value] of Object.entries(details))Object.defineProperty(e,key,{value});target.dispatchEvent(e)}
  function held(){t.expireIdle();t.step(10000);t.w.dispatchEvent(new t.w.Event('resize'));assert.equal(t.frames.size,0,'stationary contact cannot resume after >5 seconds');}
  for(const release of ['pointerup','pointercancel']){
    event(chips,'pointerdown',{pointerId:7});held();event(t.w.document,release,{pointerId:7});assert.equal(t.frames.size,0,'release starts new idle delay');assert.equal(t.idleTimers.size,1);t.expireIdle();assert.equal(t.frames.size,1);
  }
  for(const release of ['touchend','touchcancel']){
    event(chips,'touchstart',{changedTouches:[{identifier:4}]});held();event(t.w.document,release,{changedTouches:[{identifier:4}]});assert.equal(t.frames.size,0);t.expireIdle();assert.equal(t.frames.size,1);
  }
  event(chips,'pointerdown',{pointerId:1});event(chips,'pointerdown',{pointerId:2});event(t.w.document,'pointerup',{pointerId:1});held();event(t.w.document,'pointercancel',{pointerId:2});t.expireIdle();assert.equal(t.frames.size,1);
  event(chips,'touchstart',{changedTouches:[{identifier:1},{identifier:2}]});event(t.w.document,'touchend',{changedTouches:[{identifier:1}]});held();event(t.w.document,'touchcancel',{changedTouches:[{identifier:2}]});t.expireIdle();assert.equal(t.frames.size,1);
  // Both event families may describe the same physical touch; release both.
  event(chips,'pointerdown',{pointerId:3});event(chips,'touchstart',{changedTouches:[{identifier:3}]});event(t.w.document,'pointerup',{pointerId:3});held();event(t.w.document,'touchend',{changedTouches:[{identifier:3}]});t.expireIdle();assert.equal(t.frames.size,1);
  event(chips,'pointerdown',{pointerId:8});await t.w.chooseReportDate('2026-09-30');await settle();assert.equal(t.idleTimers.size,0);held();event(t.w.document,'pointerup',{pointerId:8});t.expireIdle();assert.equal(t.frames.size,1,'date reset does not strand contact after outside release');
  event(chips,'pointerdown',{pointerId:9});event(t.w,'blur');held();event(t.w,'focus');assert.equal(t.frames.size,1,'window blur clears contacts if release cannot be delivered');
  event(chips,'touchstart',{changedTouches:[{identifier:9}]});t.w.eval('ta.destroy()');assert.equal(t.idleTimers.size,0);event(t.w.document,'touchend',{changedTouches:[{identifier:9}]});event(t.w.document,'pointerup',{pointerId:9});t.expireIdle();assert.equal(t.frames.size,0);assert.equal(t.idleTimers.size,0,'destroy removes global release listeners');assert.equal(t.errors.length,0);t.w.close();
}
async function allReviewedIdentitiesAndEncoding(){
  // Expected aliases from the accepted PRSG-48 research contract, independent of implementation lookup.
  const expectedUS={SPY:'AMEX:SPY',IWM:'AMEX:IWM',QQQ:'NASDAQ:QQQ',AAPL:'NASDAQ:AAPL',MSFT:'NASDAQ:MSFT',
    GOOGL:'NASDAQ:GOOGL',NVDA:'NASDAQ:NVDA',AVGO:'NASDAQ:AVGO',WMT:'NASDAQ:WMT',TSLA:'NASDAQ:TSLA',LIN:'NASDAQ:LIN',
    JPM:'NYSE:JPM',GS:'NYSE:GS',V:'NYSE:V',TSM:'NYSE:TSM',LLY:'NYSE:LLY',JNJ:'NYSE:JNJ',ABT:'NYSE:ABT',PG:'NYSE:PG',
    KO:'NYSE:KO',HD:'NYSE:HD',MCD:'NYSE:MCD',XOM:'NYSE:XOM',COP:'NYSE:COP',SLB:'NYSE:SLB',CAT:'NYSE:CAT',GE:'NYSE:GE',UPS:'NYSE:UPS',FCX:'NYSE:FCX',NEM:'NYSE:NEM'};
  const expectedMY={'0820EA':'MYX:F4GBM-EA','0800EA':'MYX:ABFMY1','1155':'MYX:MAYBANK','1023':'MYX:CIMB',
    '0277':'MYX:CLOUDPT','0259':'MYX:SNS','0166':'MYX:INARI','0097':'MYX:VITROX','5225':'MYX:IHH','5878':'MYX:KPJ',
    '4707':'MYX:NESTLE','3689':'MYX:F&N','5296':'MYX:MRDIY','4715':'MYX:GENM','6033':'MYX:PETGAS','5681':'MYX:PETDAG',
    '5246':'MYX:WPRTS','3816':'MYX:MISC','1961':'MYX:IOICORP','5285':'MYX:SDG'};
  const universe=JSON.parse(fs.readFileSync(path.join(root,'artifacts/daily-market-brief/watchlist-universe-five.json'),'utf8'));
  const rows=universe.groups.flatMap(group=>group.instruments);
  assert.equal(rows.length,50);assert.equal(Object.keys(expectedUS).length,30);assert.equal(Object.keys(expectedMY).length,20);
  const t=mount();await settle();t.$('.nav-link[data-view="brief"]').click();
  const controller=t.w.PraesagusTA.create(t.$('#technical-view'));controller.show(true);
  controller.update({metadata:{date:'2026-10-03'},forecasts:rows});assert.equal(t.$('#ta-chips').children.length,50);
  for(const [index,row] of rows.entries()){
    const expected=(row.market==='US'?expectedUS:expectedMY)[row.ticker];assert.ok(expected,`Accepted mapping for ${row.market} ${row.ticker}`);
    assert.equal(t.w.PraesagusTA.symbol(row),expected);
    const url=t.w.PraesagusTA.external(row);assert.equal(url,'https://www.tradingview.com/chart/?symbol='+encodeURIComponent(expected));
    assert.equal(new URL(url).searchParams.get('symbol'),expected);assert.equal([...new URL(url).searchParams].length,1);
    t.$('#ta-chips').children[index].click();const script=t.$('#ta-chart script');assert.ok(script);
    assert.equal(JSON.parse(script.textContent).symbol,expected);assert.equal(t.$('#ta-external').href,url);
    assert.equal(t.$('#ta-external').hidden,false);assert.match(t.$('#ta-status').textContent,/availability is unverified/);
    assert.ok(t.$('#ta-external').textContent.includes(expected));assert.ok(t.$('#ta-chart .tradingview-widget-copyright a'));
  }
  const fn=rows.findIndex(row=>row.market==='MY'&&row.ticker==='3689');t.$('#ta-chips').children[fn].click();
  assert.match(t.$('#ta-chart script').textContent,/MYX:F&N/);assert.match(t.$('#ta-external').href,/symbol=MYX%3AF%26N$/);
  assert.doesNotMatch(t.$('#ta-external').href,/%253A|%2526/);
  const script=t.$('#ta-chart script'),frame=t.w.document.createElement('iframe');script.parentNode.querySelector('.tradingview-widget-container__widget').append(frame);await settle();
  assert.match(t.$('#ta-status').textContent,/Data availability\/delay remains unverified/);assert.equal(t.$('#ta-external').hidden,false);
  script.onerror();assert.equal(t.$('#ta-chart').children.length,0);assert.equal(t.$('#ta-external').hidden,false);
  for(const row of [{market:'US',ticker:'UNKNOWN'},{market:'US',ticker:'__proto__'},{market:'MY',ticker:'9999'},
                    {market:'MY',ticker:'9999EA'},{market:'MY',ticker:'constructor'},{market:'MY',ticker:'F&N'},
                    {market:'MY',ticker:'SPY'},{market:'US',ticker:'3689'},{market:'UK',ticker:'AAPL'},null]){
    assert.equal(t.w.PraesagusTA.symbol(row),null);assert.equal(t.w.PraesagusTA.external(row),'https://www.tradingview.com/symbols/');
  }
  for(const row of [{market:'US',ticker:'UNKNOWN'},{market:'MY',ticker:'9999'}]){
    controller.update({forecasts:[row]});assert.equal(t.$('#ta-chart').children.length,0);
    assert.equal(t.$('#ta-external').href,'https://www.tradingview.com/symbols/');assert.equal(t.$('#ta-external').hidden,false);
    assert.match(t.$('#ta-status').textContent,/No curated/);
  }
  controller.destroy();assert.equal(t.errors.length,0);t.dom.window.close();
}
(async()=>{await allReviewedIdentitiesAndEncoding();await directionsMappingAndLifecycle();await dateRacesAndErrors();await keyboardSafetyAndMotion();await deterministicTickerMotion();await heldContacts();const replay=spawnSync(process.execPath,[path.join(root,'tests/daily_report_viewer_checks.cjs')],{cwd:root,encoding:'utf8'});assert.equal(replay.status,0,replay.stdout+replay.stderr);console.log('TradingView offline DOM checks passed: all 50 reviewed identities, literal F&N/hyphen widget symbols, once-encoded URLs, unknown search fallback, unverified hosted availability, dates/races, directions, attribution, error/timeout cleanup, compact labels/44px targets, smooth reversible motion, pause/hover/focus/manual/visibility/reduced-motion guards, lifecycle cleanup, safety and existing daily viewer replay. No external scripts/network loaded.');})().catch(error=>{console.error(error);process.exitCode=1});
