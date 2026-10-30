/* Explicit saved report comparison; real DOM and retained files, network mocked. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {JSDOM,VirtualConsole}=require(path.join(process.env.DAILY_REPORT_TEST_DEPS||'/tmp/praesagus-viewer-test-deps','node_modules/jsdom'));
const root=path.resolve(__dirname,'..'),folder=path.join(root,'artifacts/daily-market-brief');
const html=fs.readFileSync(path.join(folder,'index.html'),'utf8');
const read=date=>JSON.parse(fs.readFileSync(path.join(folder,date+'.json'),'utf8'));
const clone=x=>JSON.parse(JSON.stringify(x));
async function settle(){for(let i=0;i<8;i++)await new Promise(r=>setImmediate(r))}
function mount(width=390){
  const index=JSON.parse(fs.readFileSync(path.join(folder,'reports.json'),'utf8'));
  const routes={'./reports.json':index};for(const x of index.reports)routes['./'+x.date+'.json']=read(x.date);
  const requests=[],errors=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e));
  const dom=new JSDOM(html,{url:'https://example.invalid/praesagus/daily-market-brief/?date=2026-10-21',runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,beforeParse(w){
    Object.defineProperty(w,'innerWidth',{value:width,writable:true});w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=()=>{};w.matchMedia=()=>({matches:true});w.IntersectionObserver=class{observe(){}disconnect(){}};
    w.fetch=async(url,options={})=>{requests.push({url,options});const d=routes[url];if(d==='defer')return new Promise(resolve=>routes[url]={resolve});if(d instanceof Error)throw d;return {ok:!!d,status:d?200:404,json:async()=>clone(d)}};
  }});
  return {w:dom.window,$:s=>dom.window.document.querySelector(s),routes,requests,errors,close(){assert.equal(errors.length,0);dom.window.close()}};
}
function choose(t,a,b){t.$('#compare-earlier').value=a;t.$('#compare-earlier').dispatchEvent(new t.w.Event('change'));t.$('#compare-later').value=b;t.$('#compare-later').dispatchEvent(new t.w.Event('change'))}
function groups(t,a,b){return t.w.compareSavedReports(clone(a),clone(b))}
async function realPair(width){
  const t=mount(width);await settle();assert.equal(t.$('#saved-comparison').open,false);assert.equal(t.$('#compare-earlier').value,'');assert.equal(t.$('#compare-later').value,'');assert.equal(t.$('#compare-submit').disabled,true);
  const displayed=t.w.eval('reportData'),url=t.w.location.href,count=t.requests.length;
  for(const pair of [['',''],['2026-10-20','2026-10-20'],['2026-10-21','2026-10-20'],['2026-01-01','2026-10-21']]){choose(t,...pair);assert.equal(t.$('#compare-submit').disabled,true);await t.w.compareReports();assert.equal(t.requests.length,count);}
  choose(t,'2026-10-20','2026-10-21');assert.equal(t.$('#compare-submit').disabled,false);t.$('#compare-submit').focus();await t.w.compareReports();
  assert.deepEqual(t.requests.slice(count).map(x=>x.url),['./2026-10-20.json','./2026-10-21.json']);
  assert.equal(t.w.document.activeElement,t.$('#compare-submit'));assert.equal(t.w.eval('reportData'),displayed);assert.equal(t.w.location.href,url);
  assert.match(t.$('#compare-results').textContent,/Comparing 2026-10-20 → 2026-10-21/);assert.match(t.$('#compare-results').textContent,/2026-10-20T08:01:22.284029\+08:00/);assert.match(t.$('#compare-results').textContent,/2026-10-21T08:07:10.294768\+08:00/);assert.match(t.$('#compare-results').textContent,/Revision 1/);
  assert.match(t.$('#compare-results').textContent,/Research text changed: news/);assert.match(t.$('#compare-results').textContent,/Shared calendar revisions are not compared/);assert.match(t.$('#compare-results').textContent,/Different saved forecast records/);assert.ok(t.$('#compare-results a[href="?date=2026-10-20#news"]'));assert.ok(t.$('#compare-results a[href="?date=2026-10-21#news"]'));
  const reports=[read('2026-10-20'),read('2026-10-21')],g=groups(t,...reports);assert.equal(g[0].changes.length,0);assert.equal(g[1].changes.length,50,'Recorded gap changes remain visible, never counted as new events');assert.ok(g[2].changes.length>0);assert.ok(g[2].changes.every(c=>c.type==='text'),'Only text differs; retrieval timestamps are not source changes');
  assert.equal(t.$('#compare-results .comparison-group[open] summary').textContent,'Forecast records · 50 recorded differences');
  const previous=t.$('#compare-results').innerHTML;await t.w.chooseReportDate('2026-10-20');await settle();assert.equal(t.$('#compare-results').innerHTML,previous);assert.equal(t.$('#compare-earlier').value,'2026-10-20');assert.equal(t.$('#compare-later').value,'2026-10-21');
  t.close();
}
async function pureSemantics(){
  const t=mount();await settle();const a=read('2026-10-20');let b=clone(a);
  // Timestamp-only noise, forecast order, source order and harmless whitespace do not create findings.
  b.forecasts.reverse();b.forecasts.forEach(x=>{x.forecast_as_of='2026-10-21T08:00:00+08:00';x.scenario=' \n '+x.scenario+' \t '});
  for(const section of Object.values(b.sections))for(const item of [...section.description,...section.notes]){item.text=' '+item.text.replaceAll(' ',' \n ')+' ';item.sources?.reverse();for(const s of item.sources||[])s.retrieved_at='2026-10-21T08:00:00+08:00'}
  assert.ok(groups(t,a,b).every(g=>!g.changes.length&&!g.unavailable.length));
  b=clone(a);b.forecasts.pop();let g=groups(t,a,b);assert.equal(g[0].changes.filter(c=>c.type==='membership').length,1);assert.match(g[0].changes[0].later,/Not present.*reason not recorded/);assert.doesNotMatch(JSON.stringify(g),/delisted|sold|cancelled|resolved/);
  b=clone(a);b.forecasts.push(clone(b.forecasts[0]));g=groups(t,a,b);assert.equal(g[0].changes.length,0);assert.match(g[0].unavailable[0],/Duplicate/);assert.ok(g[1].unavailable.length);
  b=clone(a);delete b.forecasts;g=groups(t,a,b);assert.ok(g[0].unavailable.length&&g[1].unavailable.length);
  b=clone(a);delete b.sections.news;g=groups(t,a,b);assert.match(g[2].unavailable.join(' '),/news/);
  b=clone(a);b.forecasts[0].direction='up';b.forecasts[0].forecast_status='available';b.forecasts[0].estimated_mid_case_value=100;g=groups(t,a,b);assert.equal(g[1].changes[0].later['Display state'],'Unrated');assert.equal(g[1].changes[0].later.Target,null,'Unsupported numbers cannot become a displayed prediction');
  b=clone(a);b.forecasts[0].confidence_reason='New recorded limitation';assert.equal(groups(t,a,b)[1].changes.length,1);
  b=clone(a);b.sections.news.description[0].sources.push(clone(b.sections.news.description[0].sources[0]));assert.equal(groups(t,a,b)[2].changes.length,0,'Duplicated source references are a set');
  b=clone(a);b.sections.news.description[0].sources[0].label='Different recorded label';assert.equal(groups(t,a,b)[2].changes[0].type,'sources');
  const before=JSON.stringify(a),unchanged=groups(t,a,a);assert.ok(unchanged.every(g=>!g.changes.length));assert.equal(JSON.stringify(a),before);
  const archive=read('2026-09-30'),archiveCopy=clone(archive);assert.ok(groups(t,archive,archiveCopy).every(g=>!g.changes.length&&!g.unavailable.length),'Existing schema2 titled paragraph cards remain supported');archiveCopy.sections.news.items[0].paragraphs[0].text='Different recorded research paragraph';assert.equal(groups(t,archive,archiveCopy)[2].changes.length,1);
  t.w.renderSavedComparison(a,clone(a));assert.match(t.$('#compare-status').textContent,/No differences found.*does not establish unchanged markets/);
  // Unsupported raw content stays escaped and unsafe URLs never become links.
  b=clone(a);b.sections.news.description[0].text='<img src=x onerror=alert(1)> <script>evil</script>';b.sections.news.description[0].sources=[{label:'<svg onload=evil>',url:'javascript:alert(1)'}];b.forecasts[0].scenario='<iframe src=x>';
  t.w.renderSavedComparison(a,b);assert.equal(t.$('#compare-results img, #compare-results script, #compare-results svg, #compare-results iframe'),null);assert.match(t.$('#compare-results').textContent,/<img/);assert.equal(t.$('#compare-results a[href^="javascript:"]'),null);
  // Unknown quotation comparability never produces a price return or price-delta finding.
  b=clone(a);b.forecasts[0].public_snapshot={price:100,source_at:a.metadata.as_of,observed_at:a.metadata.as_of,ingested_at:a.metadata.as_of,known_at:a.metadata.as_of,cutoff:a.metadata.as_of};g=groups(t,a,b);assert.equal(g[0].changes[0].subject,'Recorded quote coverage');assert.doesNotMatch(JSON.stringify(g),/return|price delta|percent/);
  const c=clone(b);c.forecasts[0].public_snapshot.price=200;assert.equal(groups(t,b,c)[0].changes.length,0,'Prices are not compared as returns');
  t.close();
}
async function failuresAndRaces(){
  const t=mount();await settle();const displayed=t.w.eval('reportData');
  for(const kind of ['missing','schema','date','calendar','cutoff']){
    const bad=read('2026-10-20');if(kind==='schema')bad.schema_version=99;if(kind==='date')bad.metadata.date='2026-10-19';if(kind==='calendar')bad.calendar_ref='../financial-calendar/2026-11.json';if(kind==='cutoff')bad.metadata.as_of='unknown';t.routes['./2026-10-20.json']=kind==='missing'?new Error('no response'):bad;
    choose(t,'2026-10-20','2026-10-21');await t.w.compareReports();assert.match(t.$('#compare-status').textContent,/Comparison unavailable: the earlier saved report/);assert.equal(t.$('#compare-results').children.length,0);assert.equal(t.w.eval('reportData'),displayed);assert.equal(t.$('#compare-submit').disabled,false);
  }
  t.routes['./2026-10-20.json']=read('2026-10-20');t.routes['./2026-10-21.json']=new Error('later missing');choose(t,'2026-10-20','2026-10-21');await t.w.compareReports();assert.match(t.$('#compare-status').textContent,/later saved report/);
  t.routes['./2026-10-21.json']=read('2026-10-21');t.routes['./2026-10-20.json']='defer';choose(t,'2026-10-19','2026-10-20');const old=t.w.compareReports();await settle();const oldResolve=t.routes['./2026-10-20.json'].resolve;const signal=t.requests.at(-1).options.signal;
  choose(t,'2026-10-20','2026-10-21');assert.equal(signal.aborted,true);assert.equal(t.$('#compare-results').children.length,0);t.routes['./2026-10-20.json']=read('2026-10-20');await t.w.compareReports();const latest=t.$('#compare-results').innerHTML;oldResolve({ok:true,json:async()=>read('2026-10-20')});await old;assert.equal(t.$('#compare-results').innerHTML,latest,'Stale ignored even if transport ignores AbortSignal');
  choose(t,'2026-10-19','2026-10-21');assert.equal(t.$('#compare-results').children.length,0,'Selection immediately invalidates old results');assert.match(t.$('#compare-status').textContent,/Choose Compare reports/);t.close();
}
(async()=>{for(const width of [390,768,1440])await realPair(width);await pureSemantics();await failuresAndRaces();console.log('Saved-report comparison checks passed: actual20/21Oct text+50recorded-gap changes, explicit indexed pair/two reads, complete context/original links, 390/768/1440 DOM, guard/null/identity/set semantics, no timestamp/reorder noise, absence not cancellation, no calendar/return inference, escapes, failed/unsupported reports, independent abort/stale handling and unchanged displayed report. Pixel/zoom/native keyboard remain browser-review required.');})().catch(e=>{console.error(e);process.exitCode=1});
