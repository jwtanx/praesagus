/* Offline landing DOM/style replay; reuses the isolated jsdom26 runtime.
 * node tests/landing_dashboard_checks.cjs
 * DOM/style checks do not measure real-browser scrolling, hit testing or overflow.
 */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM,VirtualConsole}=require(path.join(process.env.DAILY_REPORT_TEST_DEPS||'/tmp/praesagus-viewer-test-deps','node_modules/jsdom'));
const html=fs.readFileSync(path.join(__dirname,'../artifacts/index.html'),'utf8');
function mount({width=1280,reduced=false,fine=true,noJS=false,missingMedia=false,missingRAF=false}={}){
  const pending=new Map(),media=new Map(),errors=[];let serial=0,requests=0;
  const virtualConsole=new VirtualConsole();virtualConsole.on('jsdomError',e=>errors.push(e));
  const dom=new JSDOM(html,{url:'https://example.invalid/praesagus/',runScripts:noJS?'outside-only':'dangerously',pretendToBeVisual:true,virtualConsole,beforeParse(w){
    Object.defineProperty(w,'innerWidth',{value:width});
    w.fetch=()=>{requests++;throw Error('Network is forbidden in landing enhancement')};
    w.matchMedia=missingMedia?undefined:query=>{
      if(!media.has(query)){
        const listeners=new Set();media.set(query,{matches:query.includes('reduced-motion')?reduced:fine,
          addEventListener:(type,callback)=>{assert.equal(type,'change');listeners.add(callback)},
          change(matches){this.matches=matches;for(const listener of listeners)listener({matches})}});
      }
      return media.get(query);
    };
    w.requestAnimationFrame=missingRAF?undefined:callback=>{const id=++serial;pending.set(id,callback);return id};
    w.cancelAnimationFrame=id=>pending.delete(id);
  }});
  const w=dom.window,doc=w.document,cards=[...doc.querySelectorAll('.product')];
  for(const card of cards)card.getBoundingClientRect=()=>({left:20,top:10,width:300,height:200});
  function pointer(card,type='pointermove',x=70,y=50,pointerType='mouse'){
    const event=new w.Event(type,{bubbles:true,cancelable:true});Object.assign(event,{clientX:x,clientY:y,pointerType});card.dispatchEvent(event);return event;
  }
  return {dom,w,doc,cards,media,pending,errors,pointer,requests:()=>requests,flush(){const frames=[...pending.values()];pending.clear();for(const callback of frames)callback(0)}};
}
function nativeStructure(width,noJS=false){
  const t=mount({width,noJS}),{doc,w}=t;
  assert.equal(doc.querySelector('meta[http-equiv="refresh"]'),null);assert.equal(doc.querySelector('script[src]'),null);
  assert.equal(t.cards.length,2);assert.equal(doc.querySelectorAll('.products a').length,2);
  assert.deepEqual(t.cards.map(card=>card.getAttribute('href')),['daily-market-brief/','daily-market-brief/?view=technical']);
  for(const card of t.cards){
    assert.equal(card.tagName,'A');assert.equal(card.tabIndex,0);assert.equal(card.querySelector('a,button,input,select,[tabindex]'),null);
    assert.equal(card.getAttribute('onclick'),null);assert.ok(doc.getElementById(card.getAttribute('aria-labelledby')).textContent);
    assert.equal(w.getComputedStyle(card).display,'block');assert.equal(w.getComputedStyle(card).height,'100%');
    card.focus();assert.equal(doc.activeElement,card);
  }
  assert.equal(doc.querySelector('#technical-analysis a'),t.cards[1]);
  assert.equal(doc.querySelector('footer nav a').getAttribute('href'),'tickets/');
  assert.match(doc.querySelector('.disclaimer').textContent,/Research only/);
  const header=w.getComputedStyle(doc.querySelector('header'));assert.equal(header.position,'sticky');assert.equal(header.top,'0px');assert.equal(header.zIndex,'20');assert.equal(header.backgroundColor,'rgb(12, 17, 24)');
  const css=[...doc.styleSheets].flatMap(sheet=>[...sheet.cssRules]);
  assert.ok(css.some(rule=>rule.selectorText==='a:focus-visible'&&rule.style.getPropertyValue('outline').includes('3px')));
  assert.ok(css.some(rule=>rule.selectorText==='.products>article'&&rule.style.getPropertyValue('min-width')==='0'));
  const mobile=css.find(rule=>rule.conditionText==='(max-width:650px)');assert.ok(mobile);
  assert.ok([...mobile.cssRules].some(rule=>rule.selectorText==='.products'&&rule.style.getPropertyValue('grid-template-columns')==='1fr'));
  const reduced=css.find(rule=>rule.conditionText==='(prefers-reduced-motion:reduce)');assert.ok(reduced);
  assert.ok([...reduced.cssRules].some(rule=>rule.style.getPropertyValue('transition')==='none'));
  assert.ok([...reduced.cssRules].some(rule=>rule.selectorText==='.product:hover'&&rule.style.transform==='none'));
  assert.ok(css.some(rule=>rule.selectorText==='.product::before'&&rule.style.getPropertyValue('pointer-events')==='none'));
  assert.equal(t.requests(),0);assert.equal(t.errors.length,0);t.dom.window.close();
}
function tracking(){
  const t=mount(),card=t.cards[0];
  t.pointer(card);t.pointer(card,'pointermove',100,80);t.pointer(card,'pointermove',120,100);
  assert.equal(t.pending.size,1,'Pointer updates coalesce into one animation frame');
  assert.equal(card.style.getPropertyValue('--glow-x'),'');t.flush();
  assert.equal(card.style.getPropertyValue('--glow-x'),'100px');assert.equal(card.style.getPropertyValue('--glow-y'),'90px');
  t.pointer(card,'pointermove',10000,-1000);t.flush();assert.equal(card.style.getPropertyValue('--glow-x'),'300px');assert.equal(card.style.getPropertyValue('--glow-y'),'0px');
  for(const type of ['pointerleave','pointercancel','blur']){
    t.pointer(card);assert.equal(t.pending.size,1);t.pointer(card,type);assert.equal(t.pending.size,0);
    assert.equal(card.style.getPropertyValue('--glow-x'),'');t.flush();assert.equal(card.style.getPropertyValue('--glow-x'),'');
  }
  t.pointer(card);t.pointer(card,'pointermove',70,50,'touch');assert.equal(t.pending.size,0);
  assert.equal(card.style.getPropertyValue('--glow-x'),'');
  t.pointer(card);t.media.get('(prefers-reduced-motion: reduce)').change(true);assert.equal(t.pending.size,0);
  t.pointer(card);assert.equal(t.pending.size,0);t.media.get('(prefers-reduced-motion: reduce)').change(false);
  t.pointer(card);t.flush();assert.ok(card.style.getPropertyValue('--glow-x'));
  t.media.get('(hover: hover) and (pointer: fine)').change(false);assert.equal(card.style.getPropertyValue('--glow-x'),'');
  t.pointer(card);assert.equal(t.pending.size,0);
  assert.equal(t.requests(),0);assert.equal(t.errors.length,0);t.dom.window.close();
}
function disabledTracking(options){
  const t=mount(options),card=t.cards[0],event=t.pointer(card,'pointermove',70,50,options.touch?'touch':'mouse');
  assert.equal(t.pending.size,0);assert.equal(card.style.getPropertyValue('--glow-x'),'');
  assert.equal(event.defaultPrevented,false,'Touch/native navigation is not intercepted');
  assert.equal(t.requests(),0);assert.equal(t.errors.length,0);t.dom.window.close();
}
for(const width of [390,1280]){nativeStructure(width);nativeStructure(width,true)}
tracking();
for(const options of [{reduced:true},{fine:false},{touch:true},{missingMedia:true},{missingRAF:true}])disabledTracking(options);
console.log('Landing DOM/style checks passed: native whole-card links with and without JS, sticky/focus/mobile rules, bounded pointer coalescing and cleanup, touch, reduced-motion and missing-API fallback. Real-browser hit testing/scrolling/overflow not measured.');
