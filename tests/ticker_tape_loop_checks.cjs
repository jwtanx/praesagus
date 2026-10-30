/* PRSG-162 replaces the historical tape loop with explicit static selection.
 * DOM behavior only; native popup, zoom and browser pixels need visual review. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {JSDOM}=require(path.join(process.env.DAILY_REPORT_TEST_DEPS||'/tmp/praesagus-viewer-test-deps','node_modules/jsdom'));
const folder=path.join(__dirname,'../artifacts/daily-market-brief');
const code=fs.readFileSync(path.join(folder,'tradingview.js'),'utf8');
const fixture=JSON.parse(fs.readFileSync(path.join(folder,'2026-10-21.json'),'utf8'));
const dom=new JSDOM('<div id="root"><div id="ta-chips"></div><div id="ta-chart"></div><p id="ta-status"></p><p id="ta-caption"></p><a id="ta-external"></a></div>',{url:'https://example.invalid/',runScripts:'outside-only',pretendToBeVisual:true});
const w=dom.window,$=s=>w.document.querySelector(s),timers=new Map();let serial=0,raf=0;
w.requestAnimationFrame=()=>{raf++;throw Error('Static selector must never request motion')};
w.setTimeout=(fn,delay)=>{timers.set(++serial,{fn,delay});return serial};w.clearTimeout=id=>timers.delete(id);
w.eval(code);const controller=w.PraesagusTA.create($('#root'));controller.update(fixture);controller.show(true);
const search=$('#ta-search'),candidate=$('#ta-candidate'),show=$('#ta-show');
assert.equal(candidate.options.length,51);assert.equal(candidate.tagName,'SELECT');assert.equal(search.type,'search');
assert.equal($('#ta-chips [data-tape-copy]'),null);assert.equal($('#ta-chips [aria-hidden=true]'),null);
assert.equal(candidate.value,'');assert.equal(show.disabled,true);assert.match($('#ta-selected').textContent,/US · SPY — SPDR/);
const initial=$('#ta-chart script');
function query(value){search.value=value;search.dispatchEvent(new w.Event('input',{bubbles:true}))}
function choose(ticker){const option=[...candidate.options].find(x=>x.textContent.includes(' · '+ticker+' —'));assert.ok(option);candidate.value=option.value;candidate.dispatchEvent(new w.Event('change',{bubbles:true}));return option}
query('apple');assert.equal(candidate.options.length,2);assert.match(candidate.options[1].textContent,/AAPL/);assert.equal($('#ta-chart script'),initial);
choose('AAPL');assert.equal($('#ta-chart script'),initial,'Native exploration does not commit');assert.equal(show.disabled,false);
search.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));assert.equal($('#ta-chart script'),initial,'Search Enter does not commit');
show.click();assert.equal(JSON.parse($('#ta-chart script').textContent).symbol,'NASDAQ:AAPL');assert.match($('#ta-selected').textContent,/AAPL — Apple/);
const committed=$('#ta-chart script');query('Bursa no such company');assert.equal(candidate.options.length,1);assert.equal(candidate.disabled,true);assert.equal(show.disabled,true);assert.match($('#ta-count').textContent,/No instruments match/);assert.equal($('#ta-chart script'),committed);assert.match($('#ta-selected').textContent,/AAPL/);assert.equal($('#ta-external').hidden,false);
$('#ta-clear').click();assert.equal(search.value,'');assert.equal(candidate.options.length,51);assert.equal(w.document.activeElement,search);assert.equal($('#ta-chart script'),committed);assert.equal(candidate.value,'');
query('MY');assert.equal(candidate.options.length,21);choose('4707');show.click();assert.equal(JSON.parse($('#ta-chart script').textContent).symbol,'MYX:NESTLE');
query('myx:f&n');assert.equal(candidate.options.length,2);assert.match(candidate.options[1].textContent,/3689/);
$('#ta-clear').click();choose('3689');show.click();assert.match($('#ta-external').href,/symbol=MYX%3AF%26N$/);
// Neither idle, resize, hover, key, visibility nor focus events create any motion.
for(const type of ['resize','focus','blur'])w.dispatchEvent(new w.Event(type));
for(const type of ['mouseenter','mouseleave','pointerdown','pointerup','wheel','touchstart','touchend','keydown'])$('#ta-chips').dispatchEvent(new w.Event(type,{bubbles:true}));
assert.equal(raf,0);assert.ok([...timers.values()].every(t=>t.delay===15000));assert.doesNotMatch(code,/requestAnimationFrame|data-tape-copy|\b5000\b|rebuildTape/);
const active=$('#ta-chart script');controller.show(false);assert.equal($('#ta-chart').children.length,0);assert.equal(timers.size,0);controller.show(true);assert.notEqual($('#ta-chart script'),active);assert.match($('#ta-selected').textContent,/3689/);
controller.update({metadata:{date:'2026-10-30'},forecasts:[{ticker:'MSFT',market:'US',name:'Complete long company name <img src=x>'}]});assert.equal(search.value,'');assert.equal(candidate.options.length,2);assert.equal(candidate.value,'');assert.match($('#ta-selected').textContent,/MSFT/);assert.match($('#ta-caption').textContent,/2026-10-30/);assert.equal($('#root img'),null);assert.match($('#ta-selected').textContent,/<img src=x>/);
controller.update(null);assert.equal($('#ta-chart').children.length,0);assert.equal(candidate.options.length,1);assert.equal(show.disabled,true);assert.equal(search.disabled,true);assert.equal(timers.size,0);assert.match($('#ta-selected').textContent,/none/);
controller.destroy();assert.equal(timers.size,0);controller.update(fixture);assert.equal(candidate.options.length,1);assert.equal(raf,0);w.close();
console.log('Static instrument selector checks passed: all50choices, ticker/company/market/curated-alias search, 0/1/many matches, separate candidate/active identity, explicit commit, no search Enter/autoplay/clones/idle timers, Clear focus, report update, source safety and show/hide/destroy cleanup. Native popup/keyboard pixels remain browser-review required.');
