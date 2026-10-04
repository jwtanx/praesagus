/* Offline date navigation behavior; jsdom does not measure mobile layout. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {JSDOM,VirtualConsole}=require(path.join(process.env.DAILY_REPORT_TEST_DEPS||'/tmp/praesagus-viewer-test-deps','node_modules/jsdom'));
const folder=path.join(__dirname,'../artifacts/daily-market-brief');
const html=fs.readFileSync(path.join(folder,'index.html'),'utf8');
const fixture=JSON.parse(fs.readFileSync(path.join(folder,'2026-10-01.json'),'utf8'));
const calendar=JSON.parse(fs.readFileSync(path.join(folder,'../financial-calendar/2026-10.json'),'utf8'));
const dates=['2024-03-08','2024-02-29','2024-02-20','2024-03-01','2024-02-22','2024-02-29','2023-12-31','2024-01-08'];
async function settle(){for(let i=0;i<10;i++)await new Promise(resolve=>setImmediate(resolve))}
function mount({index={latest:'2024-02-29',reports:dates.map(date=>({date,label:date}))},search='?view=technical&keep=yes',failIndex=false,failReport=false}={}){
  const calls=[],pending=new Map(),errors=[],updates=[];let defer=false;
  const console=new VirtualConsole();console.on('jsdomError',error=>errors.push(error));
  const dom=new JSDOM(html,{url:'https://example.invalid/daily-market-brief/'+search,runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:console,beforeParse(w){
    w.matchMedia=()=>({matches:false});w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=()=>{};
    w.IntersectionObserver=class{observe(){}disconnect(){}};
    w.PraesagusTA={create:()=>({update:data=>updates.push(data?.metadata.date||null),show:()=>{}})};
    w.fetch=async(url,options)=>{
      calls.push({url,signal:options?.signal});
      if(url==='./reports.json')return {ok:!failIndex,status:503,json:async()=>index};
      if(url.includes('financial-calendar'))return {ok:true,json:async()=>calendar};
      if(failReport)return {ok:false,status:404};
      const date=url.slice(2,-5),data=JSON.parse(JSON.stringify(fixture));data.metadata.date=date;data.calendar_ref=`../financial-calendar/${date.slice(0,7)}.json`;
      if(defer)return new Promise(resolve=>pending.set(date,()=>resolve({ok:true,json:async()=>data})));
      return {ok:true,json:async()=>data};
    };
  }});
  const w=dom.window,$=selector=>w.document.querySelector(selector);
  return {dom,w,$,index,calls,pending,errors,updates,defer(){defer=true},step(step){return $(`[data-date-step="${step}"]`)},selected(){return new URL(w.location.href).searchParams.get('date')},close(){assert.equal(errors.length,0);w.close()}};
}
(async()=>{
  const original=JSON.stringify(dates),t=mount(),indexSnapshot=JSON.stringify(t.index);await settle();
  assert.equal(t.selected(),'2024-02-29');assert.equal(JSON.stringify(dates),original);assert.equal(JSON.stringify(t.index),indexSnapshot,'Index ordering and duplicates remain unchanged');
  assert.equal(t.$('#date-picker-button').getAttribute('aria-label'),'Choose saved report date, selected 2024-02-29');
  for(const step of [-7,-1,1,7]){const b=t.step(step);assert.equal(b.tagName,'BUTTON');assert.equal(b.type,'button');assert.ok(b.getAttribute('aria-label'));assert.equal(b.disabled,false);b.focus();assert.equal(t.w.document.activeElement,b)}
  t.step(-1).click();await settle();assert.equal(t.selected(),'2024-02-22','Day skips missing dates');
  t.step(1).click();await settle();assert.equal(t.selected(),'2024-02-29','Leap date and duplicate entries');
  t.step(7).click();await settle();assert.equal(t.selected(),'2024-03-08','Week picks first saved date at or after March 7');assert.equal(t.step(1).disabled,true);assert.equal(t.step(7).disabled,true);
  const count=t.calls.length;t.step(1).click();await settle();assert.equal(t.calls.length,count,'Disabled navigation does not fetch');
  t.step(-7).click();await settle();assert.equal(t.selected(),'2024-03-01','Previous week includes exact March 1 target');
  t.step(-7).click();await settle();assert.equal(t.selected(),'2024-02-22','Previous week skips missing February 23');
  t.step(-7).click();await settle();assert.equal(t.selected(),'2024-01-08','Week goes beyond gap only in requested direction');
  t.step(-7).click();await settle();assert.equal(t.selected(),'2023-12-31','UTC week crosses year');assert.equal(t.step(-7).disabled,true);assert.equal(t.step(-1).disabled,true);
  const url=new URL(t.w.location.href);assert.equal(url.searchParams.get('view'),'technical');assert.equal(url.searchParams.get('keep'),'yes');assert.equal(t.$('#technical-view').classList.contains('hidden'),false);
  t.$('#date-picker-button').click();assert.equal(t.$('#date-picker-button').getAttribute('aria-expanded'),'true');assert.equal(t.$('[data-report-date="2023-12-30"]').disabled,true);
  t.step(1).click();await settle();assert.equal(t.selected(),'2024-01-08');assert.equal(t.$('#date-picker-button').getAttribute('aria-expanded'),'false');
  assert.ok(t.calls.filter(c=>/^\.\/\d{4}-\d{2}-\d{2}\.json$/.test(c.url)).every(c=>dates.includes(c.url.slice(2,-5))),'Only saved reports fetched');t.close();
  const race=mount();await settle();race.defer();race.step(1).click();await settle();const stale=race.calls.findLast(c=>c.url==='./2024-03-01.json');race.step(1).click();await settle();assert.equal(stale.signal.aborted,true);
  race.pending.get('2024-03-08')();await settle();assert.equal(race.selected(),'2024-03-08');assert.equal(race.updates.at(-1),'2024-03-08');
  race.pending.get('2024-03-01')();await settle();assert.equal(race.updates.at(-1),'2024-03-08','Late response cannot replace newer report');assert.match(race.w.document.title,/2024-03-08/);race.close();
  for(const options of [{failIndex:true},{index:null},{index:{latest:'2024-02-29',reports:[null]}},{index:{latest:'2024-02-30',reports:[{date:'2024-02-30'}]}},{index:{latest:'2024-02-29',reports:[]}},{search:'?date=2024-02-28'}]){
    const bad=mount(options);await settle();for(const step of [-7,-1,1,7])assert.equal(bad.step(step).disabled,true);assert.equal(bad.$('#date-picker-button').disabled,true);assert.ok(bad.$('#report [role="alert"]'));assert.equal(bad.calls.filter(c=>/^\.\/\d{4}/.test(c.url)).length,0);bad.close();
  }
  const failed=mount({failReport:true});await settle();assert.match(failed.$('#report [role="alert"]').textContent,/HTTP 404/);assert.equal(failed.step(1).disabled,false,'Saved-date navigation remains available after a report error');failed.step(1).click();await settle();assert.equal(failed.selected(),'2024-03-01');assert.match(failed.$('#report [role="alert"]').textContent,/HTTP 404/);failed.close();
  const cal=mount({search:'?keep=yes'});await settle();cal.$('.nav-link[data-view="calendar"]').click();cal.step(1).click();await settle();assert.equal(cal.$('#calendar-view').classList.contains('hidden'),false,'Current calendar view survives date navigation');assert.equal(new URL(cal.w.location.href).searchParams.get('keep'),'yes');cal.close();
  const only=mount({index:{latest:'2024-02-29',reports:[{date:'2024-02-29'}]}});await settle();for(const step of [-7,-1,1,7])assert.equal(only.step(step).disabled,true);assert.equal(only.$('#date-picker-button').disabled,false);only.close();
  console.log('Report date navigation checks passed: saved-date day/week gaps and boundaries, malformed/failed index, availability, native focus, URL/view preservation and aborted/stale report race. Browser layout and native keyboard activation require Lead review.');
})().catch(error=>{console.error(error);process.exitCode=1});
