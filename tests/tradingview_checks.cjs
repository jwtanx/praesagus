/* Offline real-DOM tests. Existing isolated jsdom dependency; no external scripts loaded. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),{spawnSync}=require('node:child_process');
const {JSDOM,VirtualConsole}=require(path.join(process.env.DAILY_REPORT_TEST_DEPS||'/tmp/praesagus-viewer-test-deps','node_modules/jsdom'));
const root=path.resolve(__dirname,'..'),moduleCode=fs.readFileSync(path.join(root,'artifacts/daily-market-brief/tradingview.js'),'utf8'),html=fs.readFileSync(path.join(root,'artifacts/daily-market-brief/index.html'),'utf8');
const report=date=>JSON.parse(fs.readFileSync(path.join(root,'artifacts/daily-market-brief',date+'.json'),'utf8'));
const index=JSON.parse(fs.readFileSync(path.join(root,'artifacts/daily-market-brief/reports.json'),'utf8'));
async function settle(){for(let i=0;i<8;i++)await new Promise(resolve=>setImmediate(resolve))}
function mount({width=390,reduce=false,moduleMissing=false}={}){
  const routes={'./reports.json':index,'./2026-09-30.json':report('2026-09-30'),'./2026-10-01.json':report('2026-10-01'),'../financial-calendar/2026-10.json':JSON.parse(fs.readFileSync(path.join(root,'artifacts/financial-calendar/2026-10.json'),'utf8'))};
  const requests=[],errors=[],timers=new Map(),scrolls=[];let timerID=10000;
  const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e));
  const dom=new JSDOM(moduleMissing?html:html.replace('<script src="./tradingview.js"></script>','<script>'+moduleCode+'</script>'),{url:'https://example.org/praesagus/daily-market-brief/?view=technical&date=2026-10-01',runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,beforeParse(w){
    Object.defineProperty(w,'innerWidth',{value:width});w.matchMedia=()=>({matches:reduce});w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=function(options){scrolls.push(options)};w.IntersectionObserver=class{observe(){}disconnect(){}};
    const originalTimeout=w.setTimeout.bind(w),originalClear=w.clearTimeout.bind(w);w.setTimeout=(fn,delay,...args)=>{if(delay===15000){const id=++timerID;timers.set(id,fn);return id}return originalTimeout(fn,delay,...args)};w.clearTimeout=id=>{if(timers.has(id))timers.delete(id);else originalClear(id)};
    w.fetch=async(url,options)=>{requests.push({url,options});const result=routes[url];if(result==='defer')return new Promise(resolve=>routes[url]={resolve});if(result instanceof Error)throw result;return {ok:!!result,status:result?200:404,json:async()=>JSON.parse(JSON.stringify(result))}}
  }});
  const $=selector=>dom.window.document.querySelector(selector);
  return {dom,w:dom.window,$,routes,requests,errors,timers,scrolls};
}
async function directionsMappingAndLifecycle(){
  const t=mount({width:1280});await settle();
  assert.equal(t.$('#technical-view').classList.contains('hidden'),false);
  assert.match(t.$('#ta-caption').textContent,/2026-10-01/);assert.match(t.$('#ta-caption').textContent,/current or delayed, not frozen/);
  const script=t.$('#ta-chart script');assert.equal(script.src,'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js');const config=JSON.parse(script.textContent);assert.equal(config.symbol,'AMEX:SPY');assert.equal(config.allow_symbol_change,false);assert.equal(config.support_host,'https://www.tradingview.com');assert.equal(config.interval,'D');assert.equal('date' in config,false);assert.equal('forecasts' in config,false);
  assert.equal(t.$('#ta-external').hidden,false);assert.equal(t.$('#ta-external').rel,'noopener noreferrer');assert.ok(t.$('#ta-chart .tradingview-widget-copyright a'));
  assert.equal(t.w.PraesagusTA.symbol({market:'US',ticker:'AAPL'}),'NASDAQ:AAPL');assert.equal(t.w.PraesagusTA.symbol({market:'US',ticker:'UNKNOWN'}),null);assert.equal(t.w.PraesagusTA.symbol({market:'US',ticker:'__proto__'}),null);assert.equal(t.w.PraesagusTA.symbol({market:'MY',ticker:'AAPL'}),null);
  const first=t.$('#ta-chips button');assert.match(first.textContent,/❔ SPY · Unrated/);assert.equal(first.getAttribute('aria-pressed'),'true');
  const aapl=[...t.$('#ta-chips').children].find(b=>b.textContent.includes('AAPL'));aapl.click();assert.equal(JSON.parse(t.$('#ta-chart script').textContent).symbol,'NASDAQ:AAPL');assert.equal(script.isConnected,false);
  const current=t.$('#ta-chart script');script.onerror();assert.equal(current.isConnected,true,'Stale error cannot clear current widget');
  const frame=t.w.document.createElement('iframe');current.parentNode.querySelector('.tradingview-widget-container__widget').append(frame);await settle();assert.match(frame.title,/AAPL/);assert.match(t.$('#ta-status').textContent,/Data availability\/delay/);assert.equal(t.timers.size,0);
  const my=[...t.$('#ta-chips').children].find(b=>b.textContent.includes('0820EA'));my.click();assert.equal(t.$('#ta-chart').children.length,0);assert.match(t.$('#ta-status').textContent,/Bursa embed coverage is not verified/);assert.match(t.$('#ta-external').href,/MYX%3A0820EA/);
  const gs=[...t.$('#ta-chips').children].find(b=>b.textContent.includes('GS ·'));gs.click();assert.match(t.$('#ta-status').textContent,/No curated US exchange mapping/);assert.equal(t.$('#ta-external').href,'https://www.tradingview.com/symbols/');
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
  assert.equal(t.w.getComputedStyle(t.$('#ta-chips')).overflowX,'auto');assert.equal(t.w.getComputedStyle(first).minHeight,'44px');assert.equal(t.w.getComputedStyle(first).borderRadius,'999px');assert.match(html,/@media\(prefers-reduced-motion:reduce\)/);
  t.$('.nav-link[data-view="brief"]').click();const controller=t.w.PraesagusTA.create(t.$('#technical-view'));controller.show(true);controller.update({metadata:{date:'<img src=x>'},forecasts:[{ticker:'<img src=x>',market:'US'},{ticker:'javascript:evil',market:'US'},{ticker:'AAPL',market:'US',direction:'__proto__'},{ticker:'AAPL',market:'US',direction:'up'},{ticker:'1155',market:'MY',direction:'down'}]});assert.equal(t.$('#ta-chips').children.length,2);assert.match(t.$('#ta-chips').textContent,/AAPL · Unrated/);assert.equal(t.$('#technical-view img'),null);assert.equal(t.$('#technical-view').querySelectorAll('script').length,1);controller.destroy();t.dom.window.close();
  const missing=mount({moduleMissing:true});await settle();assert.match(missing.$('#ta-status').textContent,/module cannot load/);assert.equal(missing.$('#ta-external').hidden,false);assert.equal(missing.errors.length,0);missing.dom.window.close();
}
(async()=>{await directionsMappingAndLifecycle();await dateRacesAndErrors();await keyboardSafetyAndMotion();const replay=spawnSync(process.execPath,[path.join(root,'tests/daily_report_viewer_checks.cjs')],{cwd:root,encoding:'utf8'});assert.equal(replay.status,0,replay.stdout+replay.stderr);console.log('TradingView offline DOM checks passed: mapping, dates/races, directions, attribution, error/timeout cleanup, keyboard/touch sizing, reduced motion, safety and existing daily viewer replay. No external scripts/network loaded.');})().catch(error=>{console.error(error);process.exitCode=1});
