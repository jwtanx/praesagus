/* Offline real-DOM replay. No live providers or repository dependency edits.
 * npm install --prefix /tmp/praesagus-viewer-test-deps --no-package-lock --no-save jsdom@26
 * node tests/daily_report_viewer_checks.cjs
 * node tests/daily_report_viewer_checks.cjs --write-browser-fixture
 * Prints a temporary static fixture directory; serve with python3 -m http.server --directory PATH.
 * Optional DAILY_REPORT_TEST_DEPS overrides the isolated dependency directory.
 */
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
  data.forecasts = ['low', 'medium', 'high', null].map((confidence, i) => ({ ticker: `TEST${i}`, name: 'Fixture', market: 'US', country: 'us', asset_type: 'equity', sector: 'Technology', sector_category: 'technology', confidence, confidence_reason: `Reason ${i}`, direction: 'unknown', direction_label: 'Unrated', current_price_value: null, estimated_mid_case: 'Unavailable', estimated_range: 'Unavailable', sources: [source] }));
  if (version === 3) data.calendar_ref = '../financial-calendar/2026-10.json';
  else { data.calendar = { month: '2026-09', timezone: 'Asia/Kuala_Lumpur', events: [{ date: '2026-09-30', title: 'Legacy event', kind: 'event', time: 'Date only', details: 'Legacy retained', sources: [source] }] }; data.sections.calendar = { description: [{ text: 'Legacy calendar description' }], notes: [] }; }
  return data;
};
const revision = (revision, extra = {}) => ({ event_id: 'jobs', revision, recorded_at: '2026-09-29T00:00:00Z', status: 'scheduled', change_reason: 'Official initial schedule', date: '2026-10-02', kind: 'event', title: 'Employment release', time: '08:30 ET', summary: 'Outcome unknown', details: 'Fixture event', exposures: 'Market-wide', sources: [source], ...extra });
const calendar = (month = '2026-10', entries = [revision(1)]) => ({ schema_version: 1, month, timezone: 'Asia/Kuala_Lumpur', notes: [{ text: 'Frozen official schedule', sources: [source] }], entries });
const index = { latest: '2026-10-01', reports: [{ date: '2026-10-01', label: '1 October 2026' }, { date: '2026-09-30', label: '30 September 2026' }, { date: '2026-10-02', label: '2 October 2026' }] };
async function settle() { for (let i = 0; i < 8; i++) await new Promise(resolve => setImmediate(resolve)); }
function mount({ width = 1280, search = '', routes = {} } = {}) {
  const requests = [], errors = [];
  const responses = { './reports.json': index, './2026-10-01.json': report('2026-10-01'), './2026-09-30.json': report('2026-09-30', 2), '../financial-calendar/2026-10.json': calendar(), ...routes };
  const vc = new VirtualConsole(); vc.on('jsdomError', e => errors.push(e));
  const dom = new JSDOM(html, { url: `http://localhost/daily-market-brief/${search}`, runScripts: 'dangerously', pretendToBeVisual: true, virtualConsole: vc, beforeParse(w) {
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
async function navigation(width) {
  const t = mount({ width }); await settle();
  assert.equal(t.$('#subtitle').textContent, 'Fixture 2026-10-01');
  assert.equal(t.$('.sections a[href="#top10"]').textContent, 'Sector shortlist');
  for (const level of ['low', 'medium', 'high', 'unavailable']) assert.match(t.$('#forecast-rows').textContent, new RegExp(`${level} evidence confidence`));
  assert.match(t.$('#forecast-rows').textContent, /Reason 3/);
  t.click('#date-picker-button'); t.click('#picker-prev');
  assert.equal(t.$('button[data-report-date="2026-09-29"]').disabled, true);
  assert.equal(t.$('button[data-report-date="2026-09-30"]').hasAttribute('onclick'), false);
  t.click('button[data-report-date="2026-09-30"]'); await settle();
  assert.equal(t.w.document.title, 'Praesagus Daily Market Brief — 2026-09-30');
  assert.equal(t.w.location.search, '?date=2026-09-30');
  assert.equal(t.$('#selected-date-label').textContent, '30 September 2026');
  assert.equal(t.$('#date-picker-button').getAttribute('aria-expanded'), 'false');
  assert.match(t.$('#report').textContent, /2026-09-30 outlook/);
  t.click('.nav-link[data-view="calendar"]');
  assert.match(t.$('#calendar-notes').textContent, /Legacy calendar description/);
  t.click('.day[data-date="2026-09-30"]'); assert.match(t.$('#event-details').textContent, /Legacy retained/);
  t.click('#calendar-next'); await settle();
  assert.ok(t.requests.some(r => r.url === '../financial-calendar/2026-10.json'));
  assert.doesNotMatch(t.$('#event-details').textContent, /Legacy event/);
  t.click('#calendar-next'); await settle();
  assert.match(t.$('#calendar-notes').textContent, /Calendar 2026-11 unavailable/);
  assert.equal(t.$('#calendar-grid').textContent, ''); assert.equal(t.$('#event-details').textContent, '');
  assert.equal(t.errors.length, 0); t.dom.window.close();
}
async function historyAndSafety() {
  const rows = [revision(1), revision(2, { recorded_at: '2026-09-30T00:00:00Z', date: '2026-10-03', change_reason: 'Official postponement', sources: [source, { label: '<script>unsafe</script>', url: 'javascript:alert(1)' }] }), revision(3, { recorded_at: '2026-09-30T08:00:00Z', date: '2026-10-03', status: 'cancelled', change_reason: 'Official cancellation' }), revision(4, { recorded_at: '2026-10-01T00:00:01Z', title: 'Future revision must not appear', date: '2026-10-04', change_reason: 'Later rebooking' })];
  const t = mount({ routes: { '../financial-calendar/2026-10.json': calendar('2026-10', rows) } }); await settle();
  t.click('.nav-link[data-view="calendar"]'); t.click('.day[data-date="2026-10-02"]');
  assert.equal(t.$('#event-details s').textContent, '📌 Employment release');
  assert.match(t.$('#event-details .revision-reason').textContent, /Superseded: Official postponement/);
  t.click('.day[data-date="2026-10-03"]');
  assert.equal(t.$('#event-details').querySelectorAll('article').length, 2);
  assert.match(t.$('#event-details').textContent, /Cancelled: Official cancellation/);
  assert.equal(t.$('#event-details').querySelectorAll('h3 s').length, 2);
  assert.doesNotMatch(t.$('#calendar-grid').textContent, /Future revision/);
  assert.equal(t.$('.day[data-date="2026-10-04"]').querySelector('.day-marker'), null);
  assert.equal(t.$('.day[data-date="2026-10-03"]').classList.contains('has-event'), false);
  assert.equal(t.$('#event-details').querySelector('script'), null);
  for (const a of t.$('#event-details').querySelectorAll('a')) { assert.equal(a.protocol, 'https:'); assert.equal(a.rel, 'noopener noreferrer'); }
  for (const url of ['javascript:alert(1)', 'data:text/html,bad', 'https://user:secret@example.org', 'https://example.org/ bad', 'https://example.org/\\bad']) assert.equal(t.w.safeSourceUrl(url), null);
  t.dom.window.close();
}
async function activeRevisionsAndReportCalendarRace() {
  const rows = [revision(1), revision(2, { recorded_at: '2026-10-01T00:00:00Z', date: '2026-10-03', date_end: '2026-10-05', kind: 'market-closure', change_reason: 'Official date correction' })];
  const t = mount({ routes: { '../financial-calendar/2026-10.json': calendar('2026-10', rows) } }); await settle();
  assert.equal(t.$('.day[data-date="2026-10-02"]').querySelector('.day-marker').textContent, 'History only');
  for (const date of ['2026-10-03', '2026-10-04', '2026-10-05']) assert.ok(t.$(`.day[data-date="${date}"]`).classList.contains('has-closure'));
  t.click('.day[data-date="2026-10-04"]');
  assert.equal(t.$('#event-details h3 s'), null); assert.match(t.$('#event-details').textContent, /Revision 2/);
  t.dom.window.close();
  const race = mount({ routes: { '../financial-calendar/2026-10.json': 'defer' } }); await settle();
  const old = race.requests.find(r => r.url === '../financial-calendar/2026-10.json');
  await race.w.chooseReportDate('2026-09-30'); await settle(); assert.equal(old.options.signal.aborted, true);
  old.resolve(calendar()); await settle();
  assert.match(race.$('#calendar-notes').textContent, /Legacy calendar description/);
  assert.match(race.$('#event-details').textContent, /Legacy event/); race.dom.window.close();
}
async function staleAndFailures() {
  const t = mount({ routes: { './2026-09-30.json': 'defer', './2026-10-02.json': 'defer' } }); await settle();
  t.w.chooseReportDate('2026-09-30'); await settle();
  const old = t.requests.find(r => r.url === './2026-09-30.json');
  assert.equal(t.$('#summary').textContent, ''); assert.match(t.$('#report').textContent, /Loading/);
  t.w.chooseReportDate('2026-10-02'); await settle(); assert.equal(old.options.signal.aborted, true);
  const latest = t.requests.find(r => r.url === './2026-10-02.json');
  latest.resolve(report('2026-10-02')); await settle(); old.resolve(report('2026-09-30', 2)); await settle();
  assert.equal(t.w.location.search, '?date=2026-10-02'); assert.equal(t.$('#subtitle').textContent, 'Fixture 2026-10-02');
  assert.match(t.$('#report').textContent, /2026-10-02 outlook/);
  t.responses['./2026-09-30.json'] = new Error('<network failed>');
  await t.w.chooseReportDate('2026-09-30'); await settle();
  assert.match(t.$('#report [role="alert"]').textContent, /network failed/);
  assert.equal(t.$('#summary').textContent, ''); assert.equal(t.$('#footer').textContent, '');
  assert.equal(t.$('#report').querySelector('network'), null);
  const count = t.requests.length;
  await t.w.chooseReportDate('2026-02-31'); await t.w.chooseReportDate('../bad');
  assert.equal(t.requests.length, count);
  t.dom.window.close();
  for (const search of ['?date=2026-02-31', '?date=2099-01-01', '?date=..%2Fsecret']) {
    const bad = mount({ search }); await settle(); assert.match(bad.$('#report [role="alert"]').textContent, /invalid or unavailable/); assert.equal(bad.requests.length, 1); bad.dom.window.close();
  }
}
async function calendarStaleAndInvalid() {
  const t = mount({ routes: { '../financial-calendar/2026-11.json': 'defer', '../financial-calendar/2026-12.json': calendar('2026-12', [revision(1, { event_id: 'dec', date: '2026-12-01', title: 'December event' })]) } }); await settle();
  t.click('#calendar-next'); await settle(); const stale = t.requests.find(r => r.url === '../financial-calendar/2026-11.json');
  t.click('#calendar-next'); await settle(); assert.equal(stale.options.signal.aborted, true);
  stale.resolve(calendar('2026-11', [revision(1, { date: '2026-11-01', title: 'Stale November' })])); await settle();
  assert.match(t.$('#calendar-month').textContent, /December/); assert.match(t.$('#event-details').textContent, /December event/); assert.doesNotMatch(t.$('#event-details').textContent, /Stale November/);
  t.dom.window.close();
  for (const data of [calendar('2026-11'), calendar('2026-10', [revision(1, { status: 'cancelled', change_reason: '' })]), calendar('2026-10', [revision(1), revision(1)])]) {
    const bad = mount({ routes: { '../financial-calendar/2026-10.json': data } }); await settle(); assert.match(bad.$('#calendar-notes').textContent, /Unable to load calendar/); assert.equal(bad.$('#calendar-grid').textContent, ''); bad.dom.window.close();
  }
  for (const ref of ['https://example.org/calendar.json', '../financial-calendar/2026-11.json']) {
    const badRef = report('2026-10-01'); badRef.calendar_ref = ref;
    const bad = mount({ routes: { './2026-10-01.json': badRef } }); await settle(); assert.match(bad.$('#report').textContent, /Invalid shared calendar reference/); assert.equal(bad.requests.length, 2); bad.dom.window.close();
  }
  const initial = revision(1); delete initial.change_reason;
  const ok = mount({ routes: { '../financial-calendar/2026-10.json': calendar('2026-10', [initial]) } }); await settle();
  assert.doesNotMatch(ok.$('#calendar-notes').textContent, /Unable to load/); assert.match(ok.$('#event-details').textContent, /Employment release/); ok.dom.window.close();
  for (const rows of [[revision(1, { title: '' })], [revision(2)], [revision(1), revision(2)], [revision(1, { date: '2026-11-01' })], [revision(1, { recorded_at: '2026-09-29T00:00:00' })]]) {
    const bad = mount({ routes: { '../financial-calendar/2026-10.json': calendar('2026-10', rows) } }); await settle(); assert.match(bad.$('#calendar-notes').textContent, /Unable to load/); bad.dom.window.close();
  }
}
async function checkedInReports() {
  const base = path.join(root, 'artifacts/daily-market-brief');
  const reportIndex = JSON.parse(fs.readFileSync(path.join(base, 'reports.json'), 'utf8'));
  for (const item of reportIndex.reports) {
    const data = JSON.parse(fs.readFileSync(path.join(base, `${item.date}.json`), 'utf8'));
    const routes = { './reports.json': reportIndex, [`./${item.date}.json`]: data };
    if (data.schema_version === 3) routes[data.calendar_ref] = JSON.parse(fs.readFileSync(path.resolve(base, data.calendar_ref), 'utf8'));
    const t = mount({ search: `?date=${item.date}`, routes }); await settle();
    assert.equal(t.$('#report [role="alert"]'), null, `${item.date} report loads`);
    assert.equal(t.$('#calendar-notes [role="alert"]'), null, `${item.date} calendar loads`);
    assert.equal(t.$('#forecast-rows').querySelectorAll('tr').length, data.forecasts.length);
    assert.equal(t.errors.length, 0); t.dom.window.close();
  }
}
if (process.argv.includes('--write-browser-fixture')) {
  const dir = fs.mkdtempSync(path.join(require('node:os').tmpdir(), 'praesagus-report-fixture-'));
  fs.mkdirSync(path.join(dir, 'daily-market-brief')); fs.mkdirSync(path.join(dir, 'financial-calendar'));
  fs.writeFileSync(path.join(dir, 'daily-market-brief/index.html'), html);
  const write = (name, value) => fs.writeFileSync(path.join(dir, name), JSON.stringify(value, null, 2));
  write('daily-market-brief/reports.json', index);
  write('daily-market-brief/2026-10-01.json', report('2026-10-01'));
  write('daily-market-brief/2026-09-30.json', report('2026-09-30', 2));
  write('financial-calendar/2026-10.json', calendar('2026-10', [revision(1), revision(2, { recorded_at: '2026-09-30T00:00:00Z', status: 'cancelled', change_reason: 'Official cancellation; retained for audit' })]));
  console.log(dir);
} else (async () => {
  await navigation(1280); await navigation(390); await historyAndSafety(); await activeRevisionsAndReportCalendarRace(); await staleAndFailures(); await calendarStaleAndInvalid(); await checkedInReports();
  console.log('Daily report DOM checks passed: desktop/mobile date switching, schema2/3, confidence, as-of revisions/cancellations, safe sources, missing months, stale/error handling.');
})().catch(e => { console.error(e); process.exitCode = 1; });
