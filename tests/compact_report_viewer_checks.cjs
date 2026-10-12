/* Offline compact-profile DOM replay; no provider access. Uses jsdom@26 from
 * /tmp/praesagus-viewer-test-deps or DAILY_REPORT_TEST_DEPS. Native keyboard
 * details behavior additionally verified in a real browser by Lead. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM, VirtualConsole } = require(path.join(process.env.DAILY_REPORT_TEST_DEPS || '/tmp/praesagus-viewer-test-deps', 'node_modules/jsdom'));
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'artifacts/daily-market-brief/index.html'), 'utf8');
const clone = value => JSON.parse(JSON.stringify(value));
function reportText(w){const body=w.document.body.cloneNode(true);body.querySelectorAll('script,style').forEach(x=>x.remove());return body.textContent;}
const source = { label: 'Official source', url: 'https://example.org/calendar' };
const report = (date, version = 3) => {
  const data = { schema_version: version, metadata: { date, as_of: '2026-10-01T08:00:00+08:00', subtitle: `Fixture ${date}` }, summary: [{ label: 'Fixture', title: date, summary: 'Research only' }], footer: `Footer ${date}`, sections: {}, watchlist_config: { groups: [{ key: 'technology', label: 'Technology', emoji: '💻' }] }, forecasts: [] };
  for (const id of ['outlook', 'top10', 'swing', 'etfs', 'news', 'trends', 'score']) data.sections[id] = { title: `${date} ${id}`, kicker: id, description: [], notes: [], items: [], tables: [] };
  data.forecasts = ['low', 'medium', 'high', null].map((confidence, i) => ({ ticker: `TEST${i}`, name: 'Fixture', market: 'US', country: 'us', asset_type: 'equity', sector: 'Technology', sector_category: 'technology', confidence, confidence_reason: `Reason ${i}`, direction: 'unknown', direction_label: 'Unrated', current_price_value: null, estimated_mid_case: 'Unavailable', estimated_range: 'Unavailable', sources: [source], ...(i===0?{moomoo_trend:{status:'available',signal:'bullish',label:'Bullish',last_bar_date:'2026-09-30',sma5:12.5,sma20:11.5},moomoo_session_direction:{status:'available',signal:'bearish',label:'Bearish',method:'last_price-vs-prev_close_price',source_at:'2026-10-01T07:59:00Z',retrieved_at:'2026-10-01T08:00:00Z'}}:i===1?{moomoo_trend:{status:'available',signal:'bullish',label:'Bullish',last_bar_date:'2026-09-30',sma5:12.5,sma20:11.5}}:{}) }));
  if (version === 3) data.calendar_ref = '../financial-calendar/2026-10.json';
  else { data.calendar = { month: '2026-09', timezone: 'Asia/Kuala_Lumpur', events: [{ country: 'US', date: '2026-09-30', title: 'Legacy event', kind: 'event', time: 'Date only', details: 'Legacy retained', sources: [source] }] }; data.sections.calendar = { description: [{ text: 'Legacy calendar description' }], notes: [] }; }
  return data;
};
const revision = (revision, extra = {}) => ({ country: 'US', event_id: 'jobs', revision, recorded_at: '2026-09-29T00:00:00Z', status: 'scheduled', change_reason: 'Official initial schedule', date: '2026-10-02', kind: 'event', title: 'Employment release', time: '08:30 ET', summary: 'Outcome unknown', details: 'Fixture event', exposures: 'Market-wide', sources: [source], ...extra });
const calendar = (month = '2026-10', entries = [revision(1)]) => ({ schema_version: 1, month, timezone: 'Asia/Kuala_Lumpur', notes: [{ text: 'Frozen official schedule', sources: [source] }], entries });
const index = { latest: '2026-10-01', reports: [{ date: '2026-10-01', label: '1 October 2026' }, { date: '2026-09-30', label: '30 September 2026' }, { date: '2026-10-02', label: '2 October 2026' }] };
async function settle() { for (let i = 0; i < 8; i++) await new Promise(resolve => setImmediate(resolve)); }
function mount({ width = 1280, search = '', routes = {}, latestSchedule = false } = {}) {
  const requests = [], errors = [];
  const responses = { './reports.json': index, './2026-10-01.json': report('2026-10-01'), './2026-09-30.json': report('2026-09-30', 2), '../financial-calendar/2026-10.json': calendar(), ...routes };
  const vc = new VirtualConsole(); vc.on('jsdomError', e => errors.push(e));
  const dom = new JSDOM(latestSchedule?html:html.replace('<option value="report">As of selected report', '<option value="report" selected>As of selected report'), { url: `http://localhost/daily-market-brief/${search}`, runScripts: 'dangerously', pretendToBeVisual: true, virtualConsole: vc, beforeParse(w) {
    const RealDate=w.Date;
    w.Date=class extends RealDate {constructor(...args){super(...(args.length?args:['2026-10-01T12:00:00Z']))} static now(){return RealDate.parse('2026-10-01T12:00:00Z')}};
    Object.defineProperty(w, 'innerWidth', { value: width, writable:true });
    w.scrollTo = () => {}; w.HTMLElement.prototype.scrollIntoView = () => {};
    w.sectionCallbacks=[];w.IntersectionObserver = class { constructor(callback){w.sectionCallbacks.push(callback)} observe() {} disconnect() {} };
    w.fetch = (url, options = {}) => new Promise((resolve, reject) => {
      const req = { url, options, resolve: value => resolve({ ok: true, status: 200, json: async () => clone(value) }), fail: (status = 404) => resolve({ ok: false, status }), reject };
      requests.push(req);
      if (responses[url] === 'defer') return;
      if (responses[url] instanceof Error) return reject(responses[url]);
      if (responses[url] === undefined) return req.fail();
      req.resolve(responses[url]);
    });
  } });
  const w = dom.window, $ = selector => w.document.querySelector(selector);
  const click = selector => { const el = $(selector); assert.ok(el, selector); assert.ok(!el.disabled, `Enabled: ${selector}`); el.click(); };
  return { dom, w, $, click, requests, responses, errors };
}

function compactFixture(){
  const d=report('2026-10-01');d.metadata.presentation_profile='compact-v1';
  d.collection={observed_us:1,missing_us:3,observed_my:0,missing_my:0,trend_available_count:1};
  d.sections.top10.description=[{text:'Partial quote coverage; full missing reasons remain accessible.'}];
  d.sections.top10.notes=[{text:'Preserved shortlist evidence note',sources:[source]}];
  d.sections.score.description=[{text:'Cohort 120; scored denominator 0. Missing comparable closes. Recheck October 12.'}];
  d.sections.score.tables=[{columns:['Evidence'],collapsed:true,details_label:'Review all 120 blocked forecasts',rows:Array.from({length:120},(_,i)=>[{text:`Audit row ${i+1}`,sources:[source]}])}];
  for(const x of d.forecasts){x.confidence='unavailable';x.forecast_status='unavailable';x.current_price='Unavailable';x.price_as_of='No provider point';x.data_gaps=['Missing history and target model'];}
  const x=d.forecasts[0];
  x.public_snapshot={price:10,source_at:'2026-09-30T23:59:00Z',observed_at:'2026-09-30T23:59:30Z',ingested_at:'2026-09-30T23:59:40Z',known_at:'2026-09-30T23:59:50Z',cutoff:'2026-10-01T08:00:00+08:00',listing_currency:'USD',gaps:['currency_unknown','rights_unconfirmed']};
  x.moomoo_session_direction.cutoff=d.metadata.as_of;
  x.moomoo_trend.source_url='https://open.moomoo.com/api/quote/basic-data/history-kline';x.moomoo_trend.method='SMA-5-vs-SMA-20';x.moomoo_trend.bar_count=20;x.moomoo_trend.bar_dates=['2026-09-29','2026-09-30'];x.moomoo_trend.observed_at='2026-09-30T23:59:00Z';x.moomoo_trend.ingested_at='2026-09-30T23:59:40Z';x.moomoo_trend.known_at='2026-09-30T23:59:50Z';x.moomoo_trend.cutoff=d.metadata.as_of;
  d.forecasts[1].moomoo_trend={status:'unavailable',signal:'unavailable',method:'SMA-5-vs-SMA-20',reason:'history-unavailable'};
  d.forecasts[2].moomoo_session_direction={status:'available',signal:'neutral',method:'last_price-vs-prev_close_price'};
  d.forecasts[3].direction='up';d.forecasts[3].forecast_status='available';d.forecasts[3].confidence='low';
  d.forecasts[3].confidence_reason='Frozen evidence only';d.forecasts[3].forecast_model='Synthetic drift v1';d.forecasts[3].forecast_observations=20;d.forecasts[3].forecast_horizon_sessions=1;
  Object.assign(d.forecasts[3],{currency:'USD',estimated_mid_case:'US$102.00',estimated_range:'US$99.00–US$105.00',estimated_mid_case_value:102,range_low_value:99,range_high_value:105});
  d.forecasts[3].forecast_as_of='2026-10-01T07:55:00+08:00';d.forecasts[3].target_date='2026-10-02';d.forecasts[3].forecast_basis={reference_close_date:'2026-09-30',reference_close:100,reference_source:'https://example.org/close',horizon_type:'next_session',bull_case:'Synthetic demand',bear_case:'Synthetic risk',invalidation:'Below reference'};
  return d;
}
async function compactRendering(width){
  const data=compactFixture();const frozen=JSON.stringify(data);const t=mount({width,routes:{'./2026-10-01.json':data}});await settle();
  assert.match(t.$('#top10').textContent,/US 1 observed \/ 3 missing.*MY 0 observed \/ 0 missing.*Forecasts: 1 rated \/ 3 Unrated/s);
  assert.match(t.$('#top10').textContent,/Preserved shortlist evidence note/);
  assert.doesNotMatch(t.$('.compact-coverage').textContent,/Native technical event|Not collected/);
  for(const details of t.w.document.querySelectorAll('.forecast-evidence'))assert.doesNotMatch(details.textContent,/Native technical event coverage|No dated event counts/);
  assert.equal(t.$('#market-snapshot-panel').closest('details').open,false);
  const audit=t.$('#score details.compact-table');assert.ok(audit);assert.equal(audit.open,false);assert.equal(audit.querySelectorAll('tbody tr').length,120);
  assert.match(audit.querySelector('summary').textContent,/Review all 120/);
  assert.match(t.$('#score > p').textContent,/Cohort 120; scored denominator 0.*Recheck October 12/);
  audit.querySelector('summary').focus();assert.equal(t.w.document.activeElement,audit.querySelector('summary'));
  audit.querySelector('summary').click();assert.equal(audit.open,true);audit.querySelector('summary').click();assert.equal(audit.open,false);
  const row=t.$('#forecast-rows tr');assert.equal(row.dataset.price,'');
  assert.match(row.querySelector('.quote-coverage').textContent,/10.*Provider point.*unverified.*Source:.*60 seconds before/s);
  const provenance=row.querySelector('.quote-evidence');assert.equal(provenance.open,false);
  assert.match(provenance.textContent,/Observed:.*Ingested:.*Known:.*Report cutoff:.*currency unverified.*rights unconfirmed/s);
  assert.match(provenance.textContent,/Missing history and target model/);
  assert.equal(row.querySelector('.compact-forecast-reason'),null,'confidence reason lives inside details');
  assert.match(t.$('.forecast-table th:nth-child(3)').textContent,/Prediction · target \/ range/);
  const rows=t.w.document.querySelectorAll('#forecast-rows tr');
  for(const r of rows){
    const chips=r.querySelectorAll('.instrument-prediction .signal');assert.equal(chips.length,1);
    assert.equal(r.querySelector('.native-evidence,.forecast-trend,.sma-evidence,.compact-chips'),null);
    const details=r.querySelector('.forecast-evidence'),summary=details.querySelector('summary');
    assert.equal(details.open,false);assert.equal(summary.getAttribute('aria-expanded'),'false');
    assert.equal(summary.getAttribute('aria-controls'),details.querySelector('.compact-evidence').id);
    assert.match(summary.getAttribute('aria-label'),/Target.*Prediction evidence/);
    assert.equal(t.w.getComputedStyle(chips[0]).whiteSpace,'normal');
    summary.focus();assert.equal(t.w.document.activeElement,summary);
    summary.click();await settle();assert.equal(details.open,true);assert.equal(summary.getAttribute('aria-expanded'),'true');
    summary.click();await settle();assert.equal(details.open,false);assert.equal(summary.getAttribute('aria-expanded'),'false');
    assert.doesNotMatch(r.querySelector('.instrument-prediction').textContent,/Quote:|SMA:|last_price-vs-prev_close_price|SMA-5-vs-SMA-20|bullish count|bearish count/);
  }
  assert.equal(rows[0].querySelector('.prediction-chip').textContent,'Unrated · target unavailable · range unavailable');
  assert.equal(rows[0].querySelector('.prediction-target-date').textContent,'Target date unavailable · horizon unavailable');
  assert.match(rows[0].querySelector('.forecast-evidence').textContent,/Confidence reason: Reason 0.*Original report cutoff: 2026-10-01T08:00:00\+08:00/s);
  assert.equal(rows[3].querySelector('.prediction-chip').textContent,'↑ Bullish · US$102.00 · US$99.00–US$105.00');
  assert.equal(rows[3].querySelector('.prediction-target-date').textContent,'Target: 2 Oct 2026 · 1 session');
  assert.match(rows[3].querySelector('.forecast-evidence').textContent,/Evidence confidence: low.*Frozen evidence only.*Forecast issued at: 2026-10-01T07:55:00\+08:00.*Method: Synthetic drift v1.*Observations: 20.*Reference date: 2026-09-30.*Reference value: 100.*Bull case: Synthetic demand.*Bear case: Synthetic risk.*Invalidation: Below reference/s);
  assert.equal(rows[3].querySelector('.forecast-evidence a').href,'https://example.org/close');
  assert.doesNotMatch(reportText(t.w),/\b(?:moomoo|futu|yahoo|stooq)\b/i);
  t.$('#forecast-sort').value='price-desc';t.$('#forecast-sort').dispatchEvent(new t.w.Event('change'));assert.equal(t.$('#forecast-rows tr').dataset.universeOrder,'0','unverified units remain excluded from numeric sort');
  t.$('#confidence-filter').value='low';t.$('#confidence-filter').dispatchEvent(new t.w.Event('change'));assert.equal([...rows].filter(r=>!r.hidden).length,1);
  assert.equal(JSON.stringify(data),frozen,'display never mutates financial payload');
  assert.equal(t.errors.length,0);t.dom.window.close();
}
async function predictionCases(width,compact){
  const data=compactFixture();if(!compact)delete data.metadata.presentation_profile;
  const rated=clone(data.forecasts[3]);data.forecasts=[];
  const add=(name,changes)=>data.forecasts.push({...clone(rated),ticker:name,...changes});
  add('BULL',{});add('BEAR',{direction:'down'});add('FLAT',{direction:'flat'});
  for(const [name,changes] of [
    ['PARTIAL',{range_high_value:null}],['STRING',{estimated_mid_case_value:'102'}],['BOOL',{range_low_value:true}],
    ['ZERO',{range_low_value:0}],['REVERSED',{range_low_value:110}],['OUTSIDE',{estimated_mid_case_value:106}],
    ['UNIT',{currency:'MYR'}],['MISMATCH',{estimated_mid_case:'US$999'}],['TEXT',{estimated_range:'not a price'}],
    ['DIRECTION',{direction:'bullish'}],['HELD',{forecast_status:'unavailable'}],['MISSING',{direction:'unknown',confidence:'unavailable'}]
  ])add(name,changes);
  add('DATE',{target_date:'2026-02-30',forecast_horizon_sessions:0});
  data.forecasts[0].confidence_reason='Moomoo REST / Yahoo Finance / Stooq <img src=x onerror=alert(1)>';
  data.forecasts[0].forecast_basis.bull_case='<svg onload=alert(1)>';
  data.forecasts[0].sources=[{label:'Moomoo',url:'https://open.moomoo.com/api/quote/basic-data/history-kline'},{label:'Yahoo Finance historical price inputs',url:'https://finance.yahoo.com/quote/SPY/'},{label:'<script>unsafe</script>',url:'javascript:alert(1)'}];
  data.metadata.subtitle='Moomoo data · Yahoo Finance history';data.footer='Moomoo REST evidence';
  data.sections.news.notes=[{text:'Moomoo source at https://open.moomoo.com/path?foo=bar',sources:data.forecasts[0].sources}];
  const frozen=JSON.stringify(data),t=mount({width,routes:{'./2026-10-01.json':data}});await settle();
  const rows=[...t.w.document.querySelectorAll('#forecast-rows tr')];assert.equal(rows.length,16);
  assert.deepEqual(rows.slice(0,3).map(r=>r.querySelector('.prediction-chip').textContent),['↑ Bullish · US$102.00 · US$99.00–US$105.00','↓ Bearish · US$102.00 · US$99.00–US$105.00','↔ Sideways · US$102.00 · US$99.00–US$105.00']);
  for(const row of rows.slice(3,15)){assert.equal(row.querySelector('.prediction-chip').textContent,'Unrated · target unavailable · range unavailable');assert.match(row.className,/unknown/);assert.match(row.querySelector('.forecast-evidence').textContent,/Display coverage:/);}
  assert.match(rows[3].querySelector('.forecast-evidence').textContent,/incomplete, nonnumeric or unordered/);
  assert.match(rows[9].querySelector('.forecast-evidence').textContent,/units disagree or are unsupported/);
  assert.equal(rows[15].querySelector('.prediction-target-date').textContent,'Target date unavailable · horizon unavailable');
  assert.equal(rows[0].querySelector('.forecast-evidence').open,false);rows[0].querySelector('summary').click();await settle();
  assert.match(rows[0].textContent,/<img src=x onerror=alert\(1\)>/);assert.match(rows[0].textContent,/<svg onload=alert\(1\)>/);
  assert.equal(t.$('#report').querySelector('img,script'),null);assert.equal(rows[0].querySelector('svg'),null);
  assert.doesNotMatch(reportText(t.w),/\b(?:moomoo|futu|yahoo|stooq)\b|https:\/\/open\./i);
  const hrefs=[...rows[0].querySelectorAll('.forecast-evidence a')].map(a=>a.href);assert.ok(hrefs.includes('https://open.moomoo.com/api/quote/basic-data/history-kline'));assert.ok(hrefs.includes('https://finance.yahoo.com/quote/SPY/'));assert.equal(rows[0].querySelector('a[href="https://open.moomoo.com/api/quote/basic-data/history-kline"]').textContent,'Source');assert.equal(rows[0].querySelector('a[href="https://finance.yahoo.com/quote/SPY/"]').textContent,'historical data historical price inputs');
  assert.equal([...t.w.document.querySelectorAll('#report a')].some(x=>x.protocol==='javascript:'),false);
  assert.equal(t.$('#filter-count').textContent,'16 tickers · showing 1–10');t.click('#ticker-pagination-top button[data-page="2"]');assert.equal(t.$('#filter-count').textContent,'16 tickers · showing 11–16');
  assert.equal(rows.filter(r=>!r.hidden).length,6);t.$('#country-filter').value='my';t.$('#country-filter').dispatchEvent(new t.w.Event('change'));assert.equal(t.$('#filter-count').textContent,'No tickers match these filters');
  assert.equal(JSON.stringify(data),frozen);assert.equal(t.errors.length,0);t.dom.window.close();
}
async function archivedReports(){
  for(const name of fs.readdirSync(path.join(root,'artifacts/daily-market-brief')).filter(x=>/^2026-\d\d-\d\d\.json$/.test(x))){
    const data=JSON.parse(fs.readFileSync(path.join(root,'artifacts/daily-market-brief',name),'utf8')),date=data.metadata.date;
    const t=mount({search:`?date=${date}`,routes:{'./reports.json':{latest:date,reports:[{date,label:date}]},[`./${name}`]:data}});await settle();
    const rows=[...t.w.document.querySelectorAll('#forecast-rows tr')];assert.equal(rows.length,data.forecasts.length,name);
    for(const [i,row] of rows.entries()){
      assert.equal(row.querySelectorAll('.instrument-prediction .signal').length,1,name);
      const x=data.forecasts[i],chip=row.querySelector('.prediction-chip');
      if(x.direction!=='unknown'&&x.forecast_status!=='unavailable'){assert.notEqual(chip.textContent,'Unrated · target unavailable · range unavailable',`${name} ${x.ticker}: recorded supported prices stay available`);assert.ok(chip.textContent.includes(x.estimated_mid_case));assert.ok(chip.textContent.includes(x.estimated_range));}
      else assert.equal(chip.textContent,'Unrated · target unavailable · range unavailable');
    }
    assert.equal(reportText(t.w).match(/\b(?:moomoo|futu|yahoo|stooq)\b/i),null,`${name}: no branded report wording`);
    if(date==='2026-10-08'){
      const row=rows[data.forecasts.findIndex(x=>x.ticker==='SPY')];assert.equal(row.querySelector('.prediction-chip').textContent,'↑ Bullish · US$781.37 · US$764.19–US$798.94');assert.equal(row.querySelector('.prediction-target-date').textContent,'Target: 9 Oct 2026 · 3 sessions');assert.equal(t.w.document.title,'Praesagus Daily Market Brief — 2026-10-08');
    }
    assert.equal(t.errors.length,0,name);t.dom.window.close();
  }
}
async function responsiveInstrumentContract(width){
  const data=compactFixture();data.forecasts[0].name='Complete long company identity — no essential words removed';data.forecasts[0].scenario='Complete stored scenario: '+('Evidence and uncertainty remain available. '.repeat(12));
  const t=mount({width,search:'?date=2026-10-01#top10',routes:{'./2026-10-01.json':data}});await settle();
  const row=t.$('.forecast-row'),prediction=row.querySelector('.forecast-evidence'),observation=row.querySelector('.quote-evidence');
  assert.equal(row.dataset.instrument,data.forecasts[0].market+':'+data.forecasts[0].ticker);
  assert.equal(row.querySelector('.instrument-name').textContent,data.forecasts[0].name);
  assert.equal(row.querySelector('.scenario-text').firstChild.textContent,data.forecasts[0].scenario);
  assert.equal(row.querySelectorAll('.prediction-chip').length,1);assert.equal(row.querySelectorAll('.quote-evidence').length,1);
  assert.equal(observation.parentElement.className,width>=1024?'instrument-observation':'instrument-scenario');
  assert.equal(t.w.document.querySelectorAll('.forecast-table th[scope="col"]').length,4);
  const ids=[...t.w.document.querySelectorAll('[id]')].map(e=>e.id);assert.equal(new Set(ids).size,ids.length);
  for(const details of [prediction,observation])details.querySelector('summary').click();await settle();
  assert.equal(prediction.open,true);assert.equal(observation.open,true);
  const focus=observation.querySelector('summary');focus.focus();
  for(const next of [390,768,1440,390]){t.w.innerWidth=next;t.w.dispatchEvent(new t.w.Event('resize'));assert.equal(row.querySelector('.quote-evidence'),observation);assert.equal(observation.open,true);assert.equal(prediction.open,true);assert.equal(t.w.document.activeElement,focus);assert.equal(observation.parentElement.className,next>=1024?'instrument-observation':'instrument-scenario');}
  const selector=t.$('#report-section');assert.equal(selector.value,'top10');assert.equal(selector.disabled,false);
  assert.deepEqual([...selector.options].map(e=>e.value),['outlook','top10','swing','etfs','news','trends','score']);
  assert.equal(t.$('#slider,#prev,#next,.sections'),null);
  const before=t.w.location.href;selector.value='score';selector.dispatchEvent(new t.w.Event('change'));
  assert.equal(selector.value,'score');assert.equal(t.w.location.href,before,'existing date/hash semantics retained');
  selector.focus();t.w.sectionCallbacks.at(-1)([{isIntersecting:true,target:t.$('#news')}]);assert.equal(selector.value,'score','scroll observation cannot reset a focused native choice');selector.blur();t.w.sectionCallbacks.at(-1)([{isIntersecting:true,target:t.$('#news')}]);assert.equal(selector.value,'news');
  assert.equal(row.querySelector('.quote-evidence'),observation);assert.equal(observation.open,true);
  assert.equal(row.querySelector('.instrument-observation .observation-label').textContent,'Observed last · saved 2026-10-01');
  assert.match(observation.textContent,/2026-09-30T23:59:00Z.*2026-09-30T23:59:30Z.*2026-09-30T23:59:40Z.*2026-09-30T23:59:50Z.*2026-10-01T08:00:00\+08:00/s);
  assert.equal(t.errors.length,0);t.dom.window.close();
}
(async()=>{for(const width of [1440,768,390]){await responsiveInstrumentContract(width);await compactRendering(width);for(const compact of [true,false])await predictionCases(width,compact);}await archivedReports();console.log('Prediction DOM checks passed: responsive single DOM, 390/768/1440 layouts, independent disclosure state/focus across breakpoints, complete identity/scenario/provenance, section selector/deep links, all prediction guards and archived forecasts retained.');})().catch(e=>{console.error(e);process.exitCode=1});
