/* Offline measured navigation replay; DOM rectangles are stubbed, not browser layout.
 * node tests/report_navigation_checks.cjs
 */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {JSDOM,VirtualConsole}=require(path.join(process.env.DAILY_REPORT_TEST_DEPS||'/tmp/praesagus-viewer-test-deps','node_modules/jsdom'));
const folder=path.join(__dirname,'../artifacts/daily-market-brief');
const files=Object.fromEntries(['index.html','template.html'].map(file=>[file,fs.readFileSync(path.join(folder,file),'utf8')]));
const report=JSON.parse(fs.readFileSync(path.join(folder,'2026-10-01.json'),'utf8'));
const calendar=JSON.parse(fs.readFileSync(path.join(folder,'../financial-calendar/2026-10.json'),'utf8'));
const measuredCode=html=>html.match(/\/\/ Measured navigation offsets;[\s\S]*?\/\/ End measured navigation offsets\./)[0];
assert.equal(measuredCode(files['index.html']),measuredCode(files['template.html']),'Shared measured-offset behavior stays identical');
async function settle(){for(let i=0;i<8;i++)await new Promise(resolve=>setImmediate(resolve))}
function mount({file='index.html',width=1280,reduce=false,observer=true}={}){
  const errors=[],scrolls=[],resizes=[],intersections=[],media={matches:reduce};
  const state={top:width<650?64.2:56.2,open:185.2,tools:width<650?96.2:47.2};
  const virtualConsole=new VirtualConsole();virtualConsole.on('jsdomError',e=>errors.push(e));
  const dom=new JSDOM(files[file],{url:'https://example.invalid/daily-market-brief/',runScripts:'dangerously',pretendToBeVisual:true,virtualConsole,beforeParse(w){
    Object.defineProperty(w,'innerWidth',{value:width});w.matchMedia=()=>media;
    w.HTMLElement.prototype.getBoundingClientRect=function(){return {height:this.classList.contains('topbar')?(w.document.querySelector('#nav-links.open')?state.open:state.top):this.id==='brief-tools'?state.tools:0,width,left:0,top:0}};
    function offsets(){const style=w.document.documentElement.style;return {top:style.getPropertyValue('--topbar-height'),tools:style.getPropertyValue('--brief-tools-height'),scroll:style.getPropertyValue('--section-scroll-offset')}}
    w.HTMLElement.prototype.scrollIntoView=function(options){scrolls.push({id:this.id,options,offsets:offsets()})};
    w.scrollTo=options=>scrolls.push({id:'window',options,offsets:offsets()});
    w.ResizeObserver=observer?class{constructor(callback){this.callback=callback;this.targets=[];resizes.push(this)}observe(target){this.targets.push(target)}}:undefined;
    w.IntersectionObserver=class{constructor(callback){this.callback=callback;this.targets=[];intersections.push(this)}observe(target){this.targets.push(target)}disconnect(){this.disconnected=true}};
    w.fetch=async url=>({ok:true,json:async()=>url==='./reports.json'?{schema_version:1,latest:'2026-10-01',reports:[{date:'2026-10-01',label:'1 October'}]}:url.includes('financial-calendar')?calendar:report});
  }});
  const w=dom.window,$=selector=>w.document.querySelector(selector);
  return {dom,w,$,errors,scrolls,resizes,intersections,media,state,offsets(){const style=w.document.documentElement.style;return {top:style.getPropertyValue('--topbar-height'),tools:style.getPropertyValue('--brief-tools-height'),scroll:style.getPropertyValue('--section-scroll-offset')}}};
}
function structure(t,file){
  const tools=t.$('#brief-tools');assert.equal(tools.parentElement,t.w.document.body,'Sticky wrapper has full page lifetime');
  assert.equal(t.w.getComputedStyle(tools).position,'sticky');assert.equal(t.w.getComputedStyle(tools).zIndex,'9');
  assert.equal(t.w.getComputedStyle(t.$('.bar')).position,'static','Short inner bar does not constrain sticky positioning');
  const rules=[...t.w.document.styleSheets].flatMap(sheet=>[...sheet.cssRules]);
  const rule=rules.find(rule=>rule.selectorText==='#brief-tools');assert.equal(rule.style.getPropertyValue('top'),'var(--topbar-height,0px)');
  assert.equal(rule.style.getPropertyValue('background'),'#101721');
  function flattenRules(items){return items.flatMap(rule=>[rule,...(rule.cssRules?flattenRules([...rule.cssRules]):[])])}
  const panelRules=flattenRules(rules).filter(rule=>rule.selectorText==='.panel'&&rule.style.getPropertyValue('scroll-margin-top'));
  assert.ok(panelRules.length>0);
  for(const rule of panelRules)assert.match(rule.style.getPropertyValue('scroll-margin-top'),/^var\(--section-scroll-offset,/, 'Every panel offset, including nested mobile media rules, uses measured heights');
  if(file==='index.html')assert.ok(Number(t.w.getComputedStyle(t.$('.topbar')).zIndex)>9);
  else{assert.equal(t.$('.topbar'),null);assert.equal(t.w.document.querySelectorAll('.panel').length,8)}
}
async function indexChecks(width,observer=true){
  const t=mount({width,observer});await settle();structure(t,'index.html');
  const top=Math.ceil(t.state.top),tools=Math.ceil(t.state.tools);
  assert.deepEqual(t.offsets(),{top:top+'px',tools:tools+'px',scroll:top+tools+16+'px'});
  if(observer){assert.equal(t.resizes.length,1);assert.deepEqual(t.resizes[0].targets.map(el=>el.id||el.className),['topbar','brief-tools'])}
  t.$('#next').click();assert.equal(t.scrolls.at(-1).id,'top10');assert.equal(t.scrolls.at(-1).options.behavior,'smooth');assert.equal(t.scrolls.at(-1).offsets.scroll,top+tools+16+'px');
  t.media.matches=true;t.$('#slider').value=3;t.$('#slider').dispatchEvent(new t.w.Event('input'));assert.equal(t.scrolls.at(-1).id,'etfs');assert.equal(t.scrolls.at(-1).options.behavior,'auto');
  t.$('.sections a[href="#news"]').click();assert.equal(t.scrolls.at(-1).id,'news');assert.equal(t.scrolls.at(-1).options.behavior,'auto');t.$('#prev').click();assert.equal(t.scrolls.at(-1).id,'etfs');
  t.$('#menu-toggle').click();assert.equal(t.$('#menu-toggle').getAttribute('aria-expanded'),'true');assert.equal(t.offsets().top,Math.ceil(t.state.open)+'px');
  t.$('.nav-link[data-view="technical"]').click();assert.equal(t.$('#menu-toggle').getAttribute('aria-expanded'),'false');
  assert.equal(t.offsets().tools,'0px');assert.equal(t.offsets().scroll,top+16+'px');assert.equal(t.scrolls.at(-1).offsets.scroll,top+16+'px','Offsets refreshed after menu collapse before scroll');
  t.$('.nav-link[data-view="calendar"]').click();assert.equal(t.offsets().tools,'0px');
  t.state.tools=70.1;t.$('.nav-link[data-view="tickers"]').click();assert.equal(t.scrolls.at(-1).id,'top10');assert.equal(t.scrolls.at(-1).offsets.scroll,top+71+16+'px');
  t.state.top=80.1;t.state.tools=110.1;
  if(observer)t.resizes[0].callback([]);else t.w.dispatchEvent(new t.w.Event('resize'));
  assert.deepEqual(t.offsets(),{top:'81px',tools:'111px',scroll:'208px'});
  t.$('#brief-tools').hidden=true;t.w.updateNavigationOffsets();assert.equal(t.offsets().tools,'0px');
  t.$('#brief-tools').hidden=false;t.$('.nav-link[data-view="brief"]').click();
  t.state.tools=121.1;t.w.renderBrief(report);assert.equal(t.offsets().tools,'122px','Render fallback refreshes measurements');
  assert.equal(t.w.document.querySelectorAll('#report .panel').length,7);assert.equal(t.$('#slider').max,'6');
  t.state.top=NaN;t.state.tools=-1;t.w.updateNavigationOffsets();assert.deepEqual(t.offsets(),{top:'0px',tools:'0px',scroll:'16px'});
  assert.equal(t.errors.length,0);t.dom.window.close();
}
async function templateChecks(width){
  const t=mount({file:'template.html',width});await settle();structure(t,'template.html');
  const tools=Math.ceil(t.state.tools);assert.deepEqual(t.offsets(),{top:'0px',tools:tools+'px',scroll:tools+16+'px'});
  assert.equal(t.resizes.length,1);assert.deepEqual(t.resizes[0].targets.map(el=>el.id),['brief-tools']);
  t.$('#next').click();assert.equal(t.scrolls.at(-1).id,'top10');assert.equal(t.scrolls.at(-1).options.behavior,'smooth');
  t.media.matches=true;t.$('.sections a[href="#calendar"]').click();assert.equal(t.scrolls.at(-1).id,'calendar');assert.equal(t.scrolls.at(-1).options.behavior,'auto');
  t.state.tools=130.1;t.resizes[0].callback([]);assert.equal(t.offsets().scroll,'147px');
  assert.equal(t.$('#slider').max,'7');assert.match(t.$('.disclaimer').textContent,/Template notice/);
  assert.equal(t.errors.length,0);t.dom.window.close();
}
(async()=>{for(const width of [390,1280]){await indexChecks(width);await templateChecks(width)}await indexChecks(390,false);console.log('Report navigation DOM checks passed: body-level sticky tools, shared index/template measured offsets, absent topbar, mobile menu collapse, hidden views, resize/observer/render fallback and reduced-motion scrolling. Real-browser stickiness/scroll positioning not measured.');})().catch(error=>{console.error(error);process.exitCode=1});
