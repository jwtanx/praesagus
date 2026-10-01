/* Offline real-DOM dashboard regression harness, with no repo dependency edits.
 * npm install --prefix /tmp/praesagus-viewer-test-deps --no-package-lock --no-save jsdom@26
 * node tests/ticket_dashboard_checks.cjs
 * DAILY_REPORT_TEST_DEPS may override the isolated dependency directory.
 * node tests/ticket_dashboard_checks.cjs --write-browser-fixture
 * node tests/ticket_dashboard_checks.cjs --audit-json /tmp/prsg8-audit.json
 * also replays generated committed history.
 * --write-browser-fixture prints a temporary directory for python3 -m http.server --directory PATH.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { JSDOM, VirtualConsole } = require(path.join(process.env.DAILY_REPORT_TEST_DEPS || '/tmp/praesagus-viewer-test-deps', 'node_modules/jsdom'));
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'artifacts/tickets/index.html'), 'utf8');
const clone = value => JSON.parse(JSON.stringify(value));
const sha = letter => letter.repeat(40);
const commit = (letter, subject = 'PRSG-1 Deliver code') => ({ sha: sha(letter), subject, committed_at: '2026-10-01T12:00:00+08:00', url: `https://github.com/jwtanx/praesagus/commit/${sha(letter)}` });
const check = { id: 'unit', status: 'passed', description: 'Frozen test fixture', argv: ['python3', '-m', 'pytest'], cwd: '.', evidence: ['16 passed', { limitation: 'Recorded by author; not independently rerun' }] };
const review = { status: 'pending', evidence: ['Lead review not accepted yet'] };
const acceptance = [{ id: 'PRSG-1-D1', status: 'pending', description: 'Review expected behavior', evidence: [] }];
function ticket(key, extra = {}) {
  return { ticket_key: key, title: 'Catalyst inbox', description: 'Unify stored company catalysts', status: 'in_progress', tags: { type: 'feature', modules: ['backend', 'frontend'], owner_role: 'Engineer', priority: 'P1', effort_size: 'M', impact: 'high' }, created_on: '2026-10-01', updated_at: '2026-10-01T12:00:00+08:00', spec_url: `https://github.com/jwtanx/praesagus/blob/${sha('a')}/plans/PRSG-1.md`, completion_commit: null, progress: { done: 0, total: 1 }, checks: [check], acceptance, review,
    history: [{ commit: commit('a', 'PRSG-1 Plan accepted'), kind: 'plan_created', paths: ['plans/PRSG-1.md'], status: 'in_progress', progress: { done: 0, total: 1 }, checks: [{ ...check, status: 'pending', evidence: [] }], acceptance, review }, { commit: commit('b'), kind: 'delivery_commit', paths: ['backend/catalyst_services.py'], status: 'in_progress', progress: { done: 0, total: 1 }, checks: [], acceptance: [], review: {} }], ...extra };
}
const fixture = { schema_version: 1, repository_url: 'https://github.com/jwtanx/praesagus', head_sha: sha('c'), generated_from: 'committed first-parent manifest checkpoints and recognized PRSG commit activity', limitations: ['Frozen fixture does not independently prove tests or deployment.'], tickets: [
  ticket('PRSG-10', { title: 'Zulu research', description: 'Compare licensed evidence options', status: 'complete', tags: { type: 'spike', modules: ['market-research'], owner_role: 'Researcher', priority: 'P3', effort_size: 'XS', impact: 'low' }, created_on: '2026-09-29', updated_at: '2026-09-30T00:00:00Z', completion_commit: commit('d', 'PRSG-10 Complete reviewed research'), progress: { done: 1, total: 1 }, review: { status: 'accepted', evidence: ['Reviewed sources'] } }),
  ticket('PRSG-1'),
  ticket('PRSG-2', { title: 'Alpha workflow', description: 'Harness maintenance', status: 'planned', tags: { type: 'chore', modules: ['harness'], owner_role: 'Lead', priority: 'P2', effort_size: 'S', impact: 'medium-high' }, created_on: '2026-09-30', updated_at: '2026-10-01T00:00:00Z' }),
  ticket('PRSG-0', { title: 'Shared workflow activity', description: 'Commit activity only', status: 'activity_only', tags: {}, created_on: '', updated_at: '', progress: { done: 0, total: 0 }, checks: [], acceptance: [], review: {}, spec_url: null, history: [{ commit: commit('e', 'PRSG-0 Add title hook'), kind: 'delivery_commit', paths: ['scripts/install_git_hooks.sh'], status: 'activity_only', progress: { done: 0, total: 0 }, checks: [], acceptance: [], review: {} }] }),
  ticket('PRSG-3', { title: 'Removed plan', status: 'removed', tags: { type: 'bug', modules: ['backend'], owner_role: 'Engineer', priority: 'P0', effort_size: 'L', impact: 'medium' }, created_on: '2026-09-28', updated_at: '2026-10-02T00:00:00Z' })
] };
async function settle() { for (let i = 0; i < 5; i++) await new Promise(resolve => setImmediate(resolve)); }
function mount({ width = 1280, data = fixture, failure = null, deferred = false } = {}) {
  const errors = [], downloads = [], blobs = [], requested = [];
  let resolveFetch;
  const vc = new VirtualConsole(); vc.on('jsdomError', e => errors.push(e));
  const dom = new JSDOM(html, { url: 'http://localhost/tickets/', runScripts: 'dangerously', pretendToBeVisual: true, virtualConsole: vc, beforeParse(w) {
    Object.defineProperty(w, 'innerWidth', { value: width });
    w.HTMLElement.prototype.scrollIntoView = () => {};
    w.HTMLAnchorElement.prototype.click = function () { downloads.push({ href: this.href, download: this.download }); };
    w.URL.createObjectURL = blob => { blobs.push(blob); return 'blob:fixture'; }; w.URL.revokeObjectURL = () => {};
    w.fetch = url => { requested.push(url); return new Promise((resolve, reject) => { resolveFetch = () => failure instanceof Error ? reject(failure) : resolve({ ok: !failure, status: failure || 200, json: async () => clone(data) }); if (!deferred) resolveFetch(); }); };
  } });
  const w = dom.window, $ = selector => w.document.querySelector(selector);
  const change = (selector, value, type = 'change') => { $(selector).value = value; $(selector).dispatchEvent(new w.Event(type, { bubbles: true })); };
  const rows = () => [...w.document.querySelectorAll('#ticket-rows button')].map(el => el.dataset.key);
  return { dom, w, $, change, rows, errors, downloads, blobs, requested, resolve: () => resolveFetch() };
}
async function controls(width) {
  const t = mount({ width }); await settle();
  assert.deepEqual(t.requested, ['./audit.json']); assert.equal(t.$('#full-audit').getAttribute('href'), './audit.json'); assert.equal(t.$('#full-audit').download, 'praesagus-ticket-audit.json'); assert.equal(t.$('#dashboard').hidden, false);
  assert.deepEqual(t.rows(), ['PRSG-0', 'PRSG-1', 'PRSG-2', 'PRSG-3', 'PRSG-10']);
  assert.match(t.$('#result-count').textContent, /1 declared complete · 1 completion commits/);
  assert.equal(t.$('header a').getAttribute('href'), '../daily-market-brief/'); assert.match(t.$('header').textContent, /side-branch intermediate/); assert.match(t.$('header').textContent, /Frozen fixture/);
  t.change('#search', 'LICENSED', 'input'); assert.deepEqual(t.rows(), ['PRSG-10']);
  t.change('#search', 'Catalyst inbox', 'input'); assert.deepEqual(t.rows(), ['PRSG-1']);
  t.change('#search', 'prsg-2', 'input'); assert.deepEqual(t.rows(), ['PRSG-2']);
  t.$('#reset').click();
  for (const [id, value, expected] of [['#status-filter', 'activity_only', ['PRSG-0']], ['#type-filter', 'bug', ['PRSG-3']], ['#module-filter', 'frontend', ['PRSG-1']], ['#owner-filter', 'Engineer', ['PRSG-1', 'PRSG-3']]]) { t.change(id, value); assert.deepEqual(t.rows(), expected); t.$('#reset').click(); }
  t.change('#owner-filter', 'Engineer'); t.change('#module-filter', 'frontend'); t.change('#status-filter', 'in_progress'); assert.deepEqual(t.rows(), ['PRSG-1']);
  t.change('#search', 'no match', 'input'); assert.equal(t.$('#empty').hidden, false); assert.equal(t.$('#export').disabled, true); assert.equal(t.$('#table-wrap').hidden, true);
  t.$('#reset').click();
  for (const [mode, expected] of [['key', ['PRSG-0', 'PRSG-1', 'PRSG-2', 'PRSG-3', 'PRSG-10']], ['created', ['PRSG-3', 'PRSG-10', 'PRSG-2', 'PRSG-1', 'PRSG-0']], ['updated', ['PRSG-10', 'PRSG-2', 'PRSG-1', 'PRSG-3', 'PRSG-0']], ['priority', ['PRSG-3', 'PRSG-1', 'PRSG-2', 'PRSG-10', 'PRSG-0']], ['effort', ['PRSG-10', 'PRSG-2', 'PRSG-1', 'PRSG-3', 'PRSG-0']], ['impact', ['PRSG-10', 'PRSG-3', 'PRSG-2', 'PRSG-1', 'PRSG-0']], ['title', ['PRSG-2', 'PRSG-1', 'PRSG-3', 'PRSG-0', 'PRSG-10']]]) { t.change('#sort', mode); assert.deepEqual(t.rows(), expected, mode); }
  t.change('#sort', 'priority'); t.change('#order', 'desc'); assert.deepEqual(t.rows(), ['PRSG-10', 'PRSG-2', 'PRSG-1', 'PRSG-3', 'PRSG-0']);
  t.$('button[data-key="PRSG-1"]').click(); assert.equal(t.w.document.activeElement.id, 'detail');
  assert.match(t.$('#detail').textContent, /Acceptance completion has not been declared/); assert.match(t.$('#detail').textContent, /Code delivery commits: 1/);
  assert.match(t.$('#detail').textContent, /16 passed/); assert.match(t.$('#detail').textContent, /Lead review not accepted yet/);
  assert.equal(t.$('#detail .timeline').children.length, 2);
  assert.match(t.$('#detail .timeline li').textContent, /unit · pending/); assert.doesNotMatch(t.$('#detail .timeline li').textContent, /16 passed/);
  assert.equal(t.$('#detail .timeline a').textContent, sha('a')); assert.equal(t.$('#detail .timeline a').getAttribute('rel'), 'noopener noreferrer');
  t.change('#search', 'Zulu', 'input'); assert.equal(t.$('#detail').hidden, true);
  t.$('#reset').click(); t.$('button[data-key="PRSG-0"]').click(); assert.match(t.$('#detail').textContent, /PRSG-0 activity-only/); assert.match(t.$('#detail').textContent, /Acceptance completion has not been declared/);
  t.$('button[data-key="PRSG-10"]').click(); assert.match(t.$('#detail').textContent, /Declared complete in committed metadata/); assert.ok([...t.$('#detail').querySelectorAll('a')].some(a => a.textContent === sha('d')));
  assert.equal(t.errors.length, 0); t.dom.window.close();
}
async function safetyAndCsv() {
  const malicious = clone(fixture);
  malicious.limitations = ['<img src=x onerror=alert(1)>'];
  const x = malicious.tickets[1]; x.title = '=HYPERLINK("bad","<img src=x onerror=alert(1)>")'; x.description = '  +cmd'; x.spec_url = 'javascript:alert(1)';
  x.review.evidence = ['<script>evil()</script>']; x.checks[0].evidence = ['<img src=x onerror=alert(1)>']; x.history[0].commit.url = 'https://github.com.evil.example/commit/'+sha('a'); x.history[1].commit.url = 'https://user:password@github.com/o/r/commit/'+sha('b');
  const t = mount({ data: malicious }); await settle(); t.$('button[data-key="PRSG-1"]').click();
  assert.equal(t.w.document.querySelector('img'), null); assert.match(t.$('header').textContent, /<img src=x onerror=alert\(1\)>/);
  assert.equal(t.$('#detail').querySelector('img'), null); assert.equal(t.$('#detail').querySelector('script'), null);
  assert.match(t.$('#detail').textContent, /<script>evil\(\)<\/script>/);
  for (const a of t.w.document.querySelectorAll('a[target="_blank"]')) { assert.equal(a.hostname, 'github.com'); assert.equal(a.protocol, 'https:'); assert.equal(a.username, ''); }
  assert.equal(t.$('#detail .timeline').querySelectorAll('a').length, 0);
  for (const value of ['=SUM(1,2)', '+cmd', '-cmd', '@SUM(1)', '\t=cmd', '\r\n+cmd', ' \uFEFF@cmd']) assert.ok(t.w.csvCell(value).startsWith('"\''), value);
  assert.equal(t.w.csvCell('normal,"quoted"\ntext'), '"normal,""quoted""\ntext"');
  t.change('#search', 'PRSG-1', 'input');
  const csv = t.w.filteredCsv(); assert.match(csv, /"'=HYPERLINK/); assert.match(csv, /"'  \+cmd"/); assert.doesNotMatch(csv, /"PRSG-2"/);
  t.$('#export').click(); assert.equal(t.downloads[0].download, 'praesagus-ticket-audit.csv'); assert.equal(t.blobs.length, 1); assert.match(t.blobs[0].type, /text\/csv/);
  for (const url of ['http://github.com/o/r', 'https://github.com.evil.test/o/r', 'javascript:alert(1)', 'https://user:secret@github.com/o/r', 'https://github.com:444/o/r', 'https://github.com/o/r bad', 'https://github.com/o\\r']) assert.equal(t.w.safeGithubUrl(url), null);
  const invalidCommit = t.w.commitLink({ sha: '../bad', url: 'https://github.com/o/r/commit/../bad' }); assert.equal(invalidCommit.tagName, 'SPAN');
  t.dom.window.close();
}
async function loadingAndFailure() {
  const loading = mount({ deferred: true }); assert.match(loading.$('#load-status').textContent, /Loading/); assert.equal(loading.$('#dashboard').hidden, true); loading.resolve(); await settle(); assert.equal(loading.$('#dashboard').hidden, false); loading.dom.window.close();
  for (const options of [{ failure: 404 }, { failure: new Error('<network down>') }, { data: { ...fixture, schema_version: 2 } }, { data: { ...fixture, generated_from: 'working-tree' } }, { data: { ...fixture, tickets: [ticket('not-a-ticket')] } }, { data: { ...fixture, tickets: [ticket('PRSG-1'), ticket('PRSG-1')] } }]) { const t = mount(options); await settle(); assert.equal(t.$('#load-status').getAttribute('role'), 'alert'); assert.equal(t.$('#dashboard').hidden, true); assert.equal(t.$('#load-status').querySelector('network'), null); t.dom.window.close(); }
  const empty = mount({ data: { ...fixture, tickets: [] } }); await settle(); assert.match(empty.$('#result-count').textContent, /0 of 0 tickets/); assert.equal(empty.$('#empty').hidden, false); empty.dom.window.close();
}
function inconsistentFixture() {
  const data = clone(fixture);
  const failed = { commit: commit('a', 'PRSG-8 Invalid checkpoint'), kind: 'validation_failed', status: 'inconsistent', validation_error: '<img src=x onerror=alert(1)> acceptance evidence missing', paths: ['plans/PRSG-8.harness.json'], progress: { done: 0, total: 0 }, checks: [], acceptance: [], review: {} };
  data.tickets.push(ticket('PRSG-8', { title: 'Invalid metadata checkpoint', status: 'inconsistent', validation_error: failed.validation_error, completion_commit: null, progress: { done: 0, total: 0 }, checks: [], acceptance: [], review: {}, history: [failed] }));
  data.tickets.push(ticket('PRSG-9', { title: 'Corrected metadata checkpoint', status: 'complete', completion_commit: commit('f', 'PRSG-9 Correct checkpoint'), progress: { done: 1, total: 1 }, checks: [check], acceptance: [{ id: 'PRSG-9-D1', status: 'passed', evidence: ['Reviewed'] }], review: { status: 'accepted', evidence: ['Reviewed correction'] }, history: [{ ...failed, commit: commit('a', 'PRSG-9 Invalid checkpoint'), paths: ['plans/PRSG-9.harness.json'] }, { ...failed, commit: commit('f', 'PRSG-9 Correct checkpoint'), kind: 'completed', status: 'complete', validation_error: undefined, progress: { done: 1, total: 1 }, checks: [check], acceptance: [{ id: 'PRSG-9-D1', status: 'passed', evidence: ['Reviewed'] }], review: { status: 'accepted', evidence: ['Reviewed correction'] } }] }));
  return data;
}
async function inconsistentAndRecovery() {
  const t = mount({ data: inconsistentFixture() }); await settle();
  t.change('#status-filter', 'inconsistent'); assert.deepEqual(t.rows(), ['PRSG-8']);
  assert.match(t.$('#result-count').textContent, /0 declared complete · 0 completion commits/);
  t.$('button[data-key="PRSG-8"]').click();
  assert.match(t.$('#detail [role="alert"]').textContent, /acceptance evidence missing/);
  assert.match(t.$('#detail').textContent, /completion is not accepted/);
  assert.match(t.$('#detail .timeline').textContent, /validation failed/);
  assert.equal(t.$('#detail').querySelector('img'), null);
  assert.equal(t.$('#detail .timeline a').textContent, sha('a'));
  t.$('#reset').click(); t.$('button[data-key="PRSG-9"]').click();
  assert.equal(t.$('#detail [role="alert"]'), null);
  assert.match(t.$('#detail').textContent, /Declared complete in committed metadata/);
  assert.match(t.$('#detail .timeline .validation-error').textContent, /acceptance evidence missing/);
  assert.equal(t.$('#detail .timeline').children.length, 2);
  assert.match(t.$('#detail .timeline').lastChild.textContent, /Recorded status: complete/);
  assert.equal(t.$('#detail').querySelector('img'), null); assert.equal(t.errors.length, 0);t.dom.window.close();
}
async function historicalSpecification() {
  const data = clone(fixture);
  data.tickets[1].history[0].spec_url = `https://github.com/jwtanx/praesagus/blob/${sha('a')}/plans/PRSG-1.md`;
  data.tickets[1].history[1].spec_url = 'javascript:alert(1)';
  const t = mount({ data }); await settle(); t.$('button[data-key="PRSG-1"]').click();
  const specs = [...t.$('#detail .timeline').querySelectorAll('a')].filter(a => a.textContent === 'Specification at this commit');
  assert.equal(specs.length, 1); assert.equal(specs[0].href, data.tickets[1].history[0].spec_url); assert.equal(specs[0].rel, 'noopener noreferrer');
  t.dom.window.close();
}
async function generatedAudit() {
  const option = process.argv.indexOf('--audit-json'); if (option < 0) return;
  const data = JSON.parse(fs.readFileSync(process.argv[option + 1], 'utf8'));
  const t = mount({ data }); await settle();
  assert.equal(t.$('#dashboard').hidden, false, 'Generated audit loads');
  assert.equal(t.rows().length, data.tickets.length);
  for (const ticket of data.tickets) {
    t.$(`button[data-key="${ticket.ticket_key}"]`).click();
    assert.equal(t.$('#detail .timeline')?.children.length || 0, ticket.history?.length || 0);
  }
  assert.equal(t.errors.length, 0); t.dom.window.close();
}
if (process.argv.includes('--write-browser-fixture')) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'praesagus-ticket-fixture-'));
  fs.mkdirSync(path.join(dir, 'tickets')); fs.writeFileSync(path.join(dir, 'tickets/index.html'), html); fs.writeFileSync(path.join(dir, 'tickets/audit.json'), JSON.stringify(inconsistentFixture(), null, 2)); console.log(dir);
} else (async () => { await controls(1280); await controls(390); await safetyAndCsv(); await loadingAndFailure(); await inconsistentAndRecovery(); await historicalSpecification(); await generatedAudit(); console.log('Ticket dashboard DOM checks passed: search, all filters/sorts, committed evidence timeline, completion/activity separation, safe links/text, CSV neutralization/export, loading/error/empty, inconsistent checkpoints and recovery.'); })().catch(error => { console.error(error); process.exitCode = 1; });
