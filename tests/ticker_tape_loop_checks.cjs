/* Measured synthetic flex geometry and deterministic rAF; not browser pixel proof. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {JSDOM}=require(path.join(process.env.DAILY_REPORT_TEST_DEPS||'/tmp/praesagus-viewer-test-deps','node_modules/jsdom'));
const folder=path.join(__dirname,'../artifacts/daily-market-brief');
const code=fs.readFileSync(path.join(folder,'tradingview.js'),'utf8');
const fixture=JSON.parse(fs.readFileSync(path.join(folder,'2026-10-01.json'),'utf8'));
function mount({quantized=false}={}){
  const frames=new Map(),timers=new Map(),observers=[];let serial=0,width=390,scale=1;
  const dom=new JSDOM('<div id="root"><div id="ta-chips" tabindex="0" style="display:flex;gap:4px"></div><div id="ta-chart"></div><p id="ta-status"></p><p id="ta-caption"></p><a id="ta-external"></a></div>',{url:'https://example.invalid/',runScripts:'outside-only',pretendToBeVisual:true});
  const w=dom.window,chips=w.document.querySelector('#ta-chips');
  if(quantized){let readback=0;Object.defineProperty(chips,'scrollLeft',{get:()=>readback,set:value=>{readback=Math.round(value)}})}
  const media=new w.EventTarget();media.matches=false;w.matchMedia=()=>media;
  w.requestAnimationFrame=fn=>{frames.set(++serial,fn);return serial};w.cancelAnimationFrame=id=>frames.delete(id);
  w.setTimeout=(fn,delay)=>{timers.set(++serial,{fn,delay});return serial};w.clearTimeout=id=>timers.delete(id);
  w.IntersectionObserver=class{constructor(fn){this.fn=fn;observers.push(this)}observe(){this.fn([{isIntersecting:true}])}disconnect(){this.disconnected=true}};
  w.ResizeObserver=class{constructor(fn){this.fn=fn;observers.push(this)}observe(){}disconnect(){this.disconnected=true}};
  w.HTMLElement.prototype.scrollIntoView=function(){chips.scrollLeft=0};
  function itemWidth(el){return (48+(Number(el.dataset.tapeCopy??[...chips.children].indexOf(el))%5)*17.25)*scale}
  function extent(){return [...chips.children].reduce((n,el)=>n+itemWidth(el)+4,0)-4}
  Object.defineProperty(chips,'clientWidth',{get:()=>width});Object.defineProperty(chips,'scrollWidth',{get:()=>Math.max(width,extent()+4)});
  w.HTMLElement.prototype.getBoundingClientRect=function(){const list=[...chips.children],i=list.indexOf(this);if(i<0)return {left:0,right:0,width:0};const left=list.slice(0,i).reduce((n,el)=>n+itemWidth(el)+4,2)-chips.scrollLeft;return {left,right:left+itemWidth(this),width:itemWidth(this)}};
  w.eval(code);const controller=w.PraesagusTA.create(w.document.querySelector('#root'));controller.update(fixture);controller.show(true);
  return {w,chips,controller,frames,timers,media,observers,period:()=>[...chips.querySelectorAll('button')].reduce((n,el)=>n+itemWidth(el)+4,0),step(time){for(const [id,fn] of [...frames]){frames.delete(id);fn(time)}},resize(viewport,factor=1){width=viewport;scale=factor;w.dispatchEvent(new w.Event('resize'))},idle(){for(const [id,t] of [...timers])if(t.delay===5000){timers.delete(id);t.fn()}},close(){controller.destroy();assert.equal(frames.size,0);assert.equal(timers.size,0);assert.ok(observers.every(o=>o.disconnected));w.close()}};
}
const t=mount(),buttons=[...t.chips.querySelectorAll('button')];assert.equal(buttons.length,50);assert.equal(t.chips.querySelectorAll('[data-tape-copy]').length,50);
assert.equal(t.chips.querySelectorAll('button,[tabindex]').length,50,'No extra accessible tabstops in tape');
for(const copy of t.chips.querySelectorAll('[data-tape-copy]')){assert.equal(copy.tagName,'SPAN');assert.equal(copy.getAttribute('aria-hidden'),'true');assert.equal(copy.tabIndex,-1);assert.equal(copy.hasAttribute('aria-pressed'),false)}
function cycles(start){const period=t.period();let previous=t.chips.scrollLeft,wraps=0;t.step(start);for(let time=start+16;time<start+period/12*1000*3.2;time+=16){t.step(time);const position=t.chips.scrollLeft,delta=(position-previous+period)%period;assert.ok(Math.abs(delta-.192)<1e-8,'Every frame advances same pixels, including wrap');if(position<previous)wraps++;assert.ok(position>=0&&position<period);previous=position}assert.ok(wraps>=3);assert.equal(t.frames.size,1);return start+period/12*1000*3.2}
let now=cycles(0);const before=t.chips.scrollLeft;t.step(now+100000);assert.ok(((t.chips.scrollLeft-before+t.period())%t.period())<=.768+1e-8,'Large gap capped at 64ms');
const copy=t.chips.querySelector('[data-tape-copy="4"]');copy.click();assert.equal(t.frames.size,0);assert.equal(buttons[4].getAttribute('aria-pressed'),'true');assert.ok(copy.classList.contains('ta-chip-selected'));assert.equal(JSON.parse(t.w.document.querySelector('#ta-chart script').textContent).symbol,t.w.PraesagusTA.symbol(fixture.forecasts[4]));assert.equal(t.w.document.querySelectorAll('#ta-chart script').length,1);assert.equal(t.w.document.activeElement.closest('[aria-hidden="true"]'),null);
t.idle();assert.equal(t.frames.size,1);t.resize(1280,1.37);assert.equal(t.chips.querySelectorAll('button').length,50);assert.equal(t.chips.querySelectorAll('[data-tape-copy]').length,50);now=cycles(now+100100);
buttons[0].focus();assert.equal(t.frames.size,0);buttons[0].dispatchEvent(new t.w.KeyboardEvent('keydown',{key:'End',bubbles:true}));assert.equal(t.w.document.activeElement,buttons[49]);assert.equal(t.w.document.activeElement.closest('[aria-hidden="true"]'),null);buttons[49].blur();t.idle();
t.resize(10000);assert.equal(t.chips.querySelectorAll('[data-tape-copy]').length,0);assert.equal(t.frames.size,0);t.resize(390);assert.equal(t.frames.size,1);
t.media.matches=true;t.media.dispatchEvent(new t.w.Event('change'));assert.equal(t.frames.size,0);t.media.matches=false;t.media.dispatchEvent(new t.w.Event('change'));assert.equal(t.frames.size,1);
t.chips.dispatchEvent(new t.w.Event('wheel'));assert.ok([...t.timers.values()].some(x=>x.delay===5000));t.controller.show(false);assert.equal(t.frames.size,0);assert.equal(t.timers.size,0,'Hide clears both motion idle and widget timers');t.controller.show(true);
t.controller.update({forecasts:[{market:'US',ticker:'AAPL'}]});assert.equal(t.chips.querySelectorAll('button').length,1);assert.equal(t.chips.querySelectorAll('[data-tape-copy]').length,0);assert.equal(t.frames.size,0);t.controller.update(null);assert.equal(t.chips.children.length,0);assert.equal(t.frames.size,0);assert.equal(t.timers.size,0);t.close();
// Rounded browser readback must not discard subpixel accumulation on every frame.
const q=mount({quantized:true});
function quantizedCycles(start){
  const period=q.period(),initial=q.chips.scrollLeft;let previous=initial,wraps=0;
  q.step(start);
  for(let frame=1;frame<=Math.ceil(period/.192*3.2);frame++){
    q.step(start+frame*16);const expected=(initial+frame*.192)%period,position=q.chips.scrollLeft;
    assert.ok(Math.abs(position-expected)<=.500001,'Integer readback stays within half a pixel of accumulated logical movement');
    assert.ok(position>=0&&position<=Math.ceil(period));
    if(position<previous)wraps++;else assert.ok(position-previous<=1,'Quantized forward step is bounded');
    previous=position;
  }
  assert.ok(wraps>=3);assert.equal(q.frames.size,1);
}
quantizedCycles(0);
q.chips.dispatchEvent(new q.w.Event('wheel'));q.chips.scrollLeft=500;q.idle();q.step(2000000);q.step(2001600);assert.equal(q.chips.scrollLeft,501,'Manual resume reads actual offset, with long gap capped');
q.resize(1280,1.37);quantizedCycles(3000000);
q.close();
console.log('Ticker tape loop checks passed: 3+ cycles at variable fractional widths and integer scroll readback, manual resume, invariant wrap, resize/no-overflow, large gap, 50 canonical choices, nonfocusable hidden copies/click mapping/selection, canonical keyboard focus, reduced motion and update/hide/destroy cleanup. Browser pixel continuity remains review-required.');
