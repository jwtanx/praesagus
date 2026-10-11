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
    Object.defineProperty(w, 'innerWidth', { value: width });
    w.scrollTo = () => {}; w.HTMLElement.prototype.scrollIntoView = () => {};
    w.IntersectionObserver = class { observe() {} disconnect() {} };
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
  d.forecasts[3].forecast_as_of='2026-10-01T07:55:00+08:00';d.forecasts[3].target_date='2026-10-02';d.forecasts[3].forecast_basis={reference_close_date:'2026-09-30',reference_close:100,reference_source:'https://example.org/close',horizon_type:'next_session',bull_case:'Synthetic demand',bear_case:'Synthetic risk',invalidation:'Below reference'};
  return d;
}
async function compactRendering(width){
  const data=compactFixture();const t=mount({width,routes:{'./2026-10-01.json':data}});await settle();
  assert.match(t.$('#top10').textContent,/US 1 observed \/ 3 missing.*MY 0 observed \/ 0 missing.*SMA available: 1.*Forecasts: 1 rated \/ 3 Unrated/s);
  assert.match(t.$('#top10').textContent,/Preserved shortlist evidence note/);
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
  assert.equal(row.querySelector('.compact-forecast-reason').closest('details'),null);
  assert.match(row.querySelector('.compact-forecast-reason').textContent,/Reason 0/);
  const chips=row.querySelectorAll('.compact-chips > details > summary > .signal');
  assert.deepEqual([...chips].map(x=>x.textContent),['Quote: Bearish','SMA: Bullish','Forecast: Unrated']);
  assert.match(chips[0].className,/bearish/);assert.match(chips[1].className,/bullish/);assert.match(chips[2].className,/unknown/);
  for(const chip of chips){const details=chip.closest('details');assert.equal(details.open,false);assert.ok(chip.getAttribute('aria-label').includes(chip.textContent));details.querySelector('summary').focus();assert.equal(t.w.document.activeElement,details.querySelector('summary'));details.querySelector('summary').click();assert.equal(details.open,true);}
  assert.match(row.querySelector('.compact-chips .quote-evidence').textContent,/last_price-vs-prev_close_price.*source_at.*retrieved_at.*cutoff/s);
  assert.match(row.querySelector('.sma-evidence').textContent,/SMA-5-vs-SMA-20.*bar_count: 20.*sma5: 12.5.*sma20: 11.5.*known_at/s);
  assert.match(row.querySelector('.sma-evidence').textContent,/source_url: https:\/\/open\.moomoo\.com\/api\/quote\/basic-data\/history-kline/);
  const rows=t.w.document.querySelectorAll('#forecast-rows tr');
  assert.match(rows[1].querySelector('.sma-evidence').textContent,/Unavailable.*history-unavailable/s);
  assert.match(rows[2].querySelector('.compact-chips').textContent,/Quote: Neutral/);
  assert.match(rows[3].querySelector('.forecast-evidence').textContent,/Forecast: Up.*low evidence confidence.*Synthetic drift v1.*forecast_observations: 20.*reference_close.*bull_case.*bear_case.*invalidation/s);
  t.$('#forecast-sort').value='price-desc';t.$('#forecast-sort').dispatchEvent(new t.w.Event('change'));assert.equal(t.$('#forecast-rows tr').dataset.universeOrder,'0','unverified units remain excluded from numeric sort');
  assert.equal(t.errors.length,0);t.dom.window.close();
}
async function safetyAndLegacy(){
  const data=compactFixture();data.forecasts[0].data_gaps.push('<img src=x onerror=alert(1)>');
  data.forecasts[0].moomoo_session_direction.reason='<svg onload=alert(1)>';
  data.forecasts[0].moomoo_trend.source_url='<svg onload=alert(1)>';
  data.sections.score.tables[0].details_label='<img src=x>';
  data.sections.score.tables[0].rows[0][0].sources=[{label:'<script>unsafe</script>',url:'javascript:alert(1)'}];
  const t=mount({routes:{'./2026-10-01.json':data}});await settle();
  assert.equal(t.$('#report').querySelector('img,svg,script'),null);assert.match(t.$('#report').textContent,/<img src=x>/);
  assert.equal([...t.w.document.querySelectorAll('#report a')].some(x=>x.protocol==='javascript:'),false);
  assert.equal(t.errors.length,0);t.dom.window.close();
  delete data.metadata.presentation_profile;
  const legacy=mount({routes:{'./2026-10-01.json':data}});await settle();
  assert.equal(legacy.$('#score .compact-table'),null);assert.equal(legacy.$('#score').querySelectorAll('tbody tr').length,120);
  assert.equal(legacy.$('#forecast-rows .compact-chips'),null);assert.ok(legacy.$('#forecast-rows .forecast-trend'));
  assert.equal(legacy.errors.length,0);legacy.dom.window.close();
}
(async()=>{await compactRendering(1280);await compactRendering(390);await safetyAndLegacy();console.log('Compact DOM checks passed: native closed audit/provenance/signal details, independent Quote/SMA/Forecast states and conflicts, focus/tap expansion, complete evidence, partial coverage, unsortable provider units, escaping, legacy display at desktop/mobile viewport widths.');})().catch(e=>{console.error(e);process.exitCode=1});
