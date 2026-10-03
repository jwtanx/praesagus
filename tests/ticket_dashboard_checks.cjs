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
  assert.deepEqual(t.rows(), ['PRSG-10', 'PRSG-3', 'PRSG-2', 'PRSG-1', 'PRSG-0']);
  assert.equal(t.$('#order').value,'desc');
  assert.deepEqual([...t.w.document.querySelectorAll('thead th')].slice(0,2).map(el=>el.textContent), ['Ticket','Title']);
  const row=t.$('button[data-key="PRSG-1"]').closest('tr');assert.equal(row.children[0].textContent,'PRSG-1');assert.equal(row.children[1].textContent,'Catalyst inbox');assert.equal(row.children.length,7);assert.match(row.children[6].textContent,/MYT/);assert.equal(row.children[6].querySelector('time').dateTime,fixture.tickets[1].updated_at);
  for(const [key,emoji,color] of [['PRSG-10','✅','complete'],['PRSG-1','🔄','progress'],['PRSG-2','📝','planned']]){const badge=t.$(`button[data-key="${key}"]`).closest('tr').querySelector('.status-badge');assert.ok(badge.classList.contains(`status-${color}`));assert.equal(badge.firstChild.textContent,emoji);assert.equal(badge.firstChild.getAttribute('aria-hidden'),'true');assert.ok(badge.lastChild.textContent);}
  assert.equal(t.$('header a[href="../"]').textContent,'← Home');
  assert.match(t.$('#result-count').textContent, /1 declared complete · 1 completion commits/);
  assert.equal(t.$('header a[href="../daily-market-brief/"]').getAttribute('href'), '../daily-market-brief/'); assert.match(t.$('header').textContent, /side-branch intermediate/); assert.match(t.$('header').textContent, /Frozen fixture/);
  t.change('#search', 'LICENSED', 'input'); assert.deepEqual(t.rows(), ['PRSG-10']);
  t.change('#search', 'Catalyst inbox', 'input'); assert.deepEqual(t.rows(), ['PRSG-1']);
  t.change('#search', 'prsg-2', 'input'); assert.deepEqual(t.rows(), ['PRSG-2']);
  t.$('#reset').click();
  assert.equal(t.$('#order').value,'desc');
  for (const [id, value, expected] of [['#status-filter', 'activity_only', ['PRSG-0']], ['#type-filter', 'bug', ['PRSG-3']], ['#module-filter', 'frontend', ['PRSG-1']], ['#owner-filter', 'Engineer', ['PRSG-3', 'PRSG-1']]]) { t.change(id, value); assert.deepEqual(t.rows(), expected); t.$('#reset').click(); }
  t.change('#owner-filter', 'Engineer'); t.change('#module-filter', 'frontend'); t.change('#status-filter', 'in_progress'); assert.deepEqual(t.rows(), ['PRSG-1']);
  t.change('#search', 'no match', 'input'); assert.equal(t.$('#empty').hidden, false); assert.equal(t.$('#export').disabled, true); assert.equal(t.$('#table-wrap').hidden, true);
  t.$('#reset').click();
  t.change('#order','asc');
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
async function decisionOverviewAndDisclosures(width) {
  const data=clone(fixture),row=data.tickets[1];
  const long='Authored source wording '+ 'readable evidence '.repeat(45)+'\n\nFinal recorded paragraph.';
  row.decision_context={fields:{purpose:{text:['User needs readable reasons.','Second full purpose block.'],source:'manifest'},approach:{text:['Recorded proposal using native details.'],source:'manifest'},choices:{text:['Native disclosure; external viewer.'],source:'manifest'},findings:{text:[long],source:'named specification sections'},tradeoffs:{text:['No dependency; no generated rationale.'],source:'manifest'}},references:[{label:'Official research',url:'https://example.org/research'},{label:'Unsafe credentials',url:'https://user:secret@example.org'},{label:'Unsafe protocol',url:'javascript:alert(1)'},{label:'Unsafe encoded control',url:'https://example.org/%0aunsafe'}]};
  const t=mount({width,data});await settle();t.$('button[data-key="PRSG-1"]').click();
  const overview=t.$('#detail .decision-overview'),references=t.$('#detail .decision-references'),technical=t.$('#detail .technical-details');
  assert.equal(overview.closest('details'),null,'Overview visible outside disclosures');
  assert.deepEqual([...overview.querySelectorAll('h3')].map(el=>el.textContent),['Why','Approach','Options','Findings','Tradeoffs / decision']);
  assert.match(overview.textContent,/Second full purpose block/);assert.match(overview.textContent,/User needs readable reasons/);assert.ok(overview.textContent.includes(long));
  assert.equal(t.$('#detail .decision-context'),null);
  assert.ok([...overview.querySelectorAll('p')].some(el=>el.textContent.length>240));
  assert.ok(overview.compareDocumentPosition(references)&t.w.Node.DOCUMENT_POSITION_FOLLOWING);
  assert.equal(technical.querySelector('summary').textContent,'Technical details & audit history');assert.equal(technical.open,false);
  assert.ok(overview.compareDocumentPosition(technical)&t.w.Node.DOCUMENT_POSITION_FOLLOWING);
  assert.equal(technical.querySelector('.timeline').children.length,2);
  assert.match(technical.textContent,/16 passed/);assert.match(technical.textContent,/Current acceptance/);assert.ok(technical.querySelector('dl'));
  assert.equal(t.$('#detail-title').closest('details'),null);
  assert.match(overview.textContent,/source wording alone does not establish acceptance/);
  const borderRule=[...t.w.document.styleSheets].flatMap(sheet=>[...sheet.cssRules]).find(rule=>rule.selectorText==='.technical-details');
  assert.match(borderRule.style.getPropertyValue('border'),/^1px solid/); // jsdom cannot resolve var() inside border shorthand.
  assert.equal(t.w.getComputedStyle(technical).padding,'12px');
  technical.querySelector('summary').click();assert.equal(technical.open,true);
  const checks=[...technical.querySelectorAll('details')].find(el=>el.querySelector('summary')?.textContent==='Current checks');assert.equal(checks.open,false);checks.querySelector('summary').click();assert.equal(checks.open,true);
  const source=references.querySelector('a[href="https://example.org/research"]');assert.ok(source);assert.equal(source.rel,'noopener noreferrer');assert.equal(references.querySelectorAll('a').length,1);
  assert.equal(t.w.getComputedStyle(overview.querySelector('.decision-text')).overflowWrap,'anywhere');
  for(const url of ['javascript:alert(1)','http://example.org','https://u:p@example.org','https://example.org/\nunsafe','https://example.org/%00unsafe','https://example.org/%7funsafe','https://example.org/back\\slash'])assert.equal(t.w.safeReferenceUrl(url),null,url);
  t.dom.window.close();
}
async function decisionFallbackAndSafety() {
  const data=clone(fixture);const context={fields:{purpose:{text:['<img src=x onerror=alert(1)>'],source:'manifest'},findings:{text:[{bad:'object'}],source:'manifest'}},references:[{label:'<script>evil()</script>',url:'https://example.org/safe'}]};
  data.tickets[1].decision_context=context;
  for(const row of data.tickets.filter(row=>['removed','activity_only'].includes(row.status)))row.decision_context=context;
  data.tickets.push(ticket('PRSG-8',{status:'inconsistent',decision_context:context}));
  const t=mount({data});await settle();
  t.$('button[data-key="PRSG-1"]').click();assert.equal(t.$('#detail').querySelector('img'),null);assert.equal(t.$('#detail').querySelector('script'),null);assert.match(t.$('.decision-overview').textContent,/<img src=x/);assert.match(t.$('.decision-overview').textContent,/Not recorded/);
  for(const key of ['PRSG-0','PRSG-3','PRSG-8']){t.change('#search',key,'input');t.$(`button[data-key="${key}"]`).click();assert.doesNotMatch(t.$('.decision-overview').textContent,/<img|evil/);assert.match(t.$('.decision-overview').textContent,/Current decision context unavailable/);assert.equal(t.$('.decision-overview').querySelectorAll('p').length,5);}
  t.change('#search','PRSG-2','input');t.$('button[data-key="PRSG-2"]').click();assert.match(t.$('#detail').textContent,/Harness maintenance/);assert.equal(t.$('.decision-overview').querySelectorAll('p').length,5);assert.ok([...t.$('.decision-overview').querySelectorAll('p')].every(el=>el.textContent==='Not recorded.'));
  assert.equal(t.errors.length,0);t.dom.window.close();
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
function landingChecks(){
  const file=path.join(root,'artifacts/index.html');const dom=new JSDOM(fs.readFileSync(file,'utf8'),{url:'http://localhost/praesagus/'}),doc=dom.window.document;
  assert.equal(doc.querySelector('meta[http-equiv="refresh"]'),null);
  assert.equal(doc.querySelector('script[src]'),null,'Landing enhancements have no external script dependency');
  assert.match(doc.querySelector('h1').textContent,/Understand the market/);
  assert.doesNotMatch(doc.querySelector('h1').textContent,/Choose your dashboard/);
  const products=doc.querySelector('section[aria-label="Research dashboards"]');
  assert.deepEqual([...products.querySelectorAll('h2')].map(el=>el.textContent),['Report dashboard','Technical analysis']);
  assert.equal(products.querySelector('a').getAttribute('href'),'daily-market-brief/');
  assert.equal(doc.querySelector('#technical-analysis .coming-soon'),null);
  assert.equal(doc.querySelector('#technical-analysis a').getAttribute('href'),'daily-market-brief/?view=technical');
  assert.equal(products.querySelector('a[href="tickets/"]'),null);
  assert.equal(doc.querySelector('footer nav[aria-label="Project utilities"] a').getAttribute('href'),'tickets/');
  for(const link of doc.querySelectorAll('a'))assert.ok(fs.existsSync(path.join(root,'artifacts',link.getAttribute('href').split(/[?#]/)[0],'index.html')));
  dom.window.close();
}
async function generatedAudit() {
  const option = process.argv.indexOf('--audit-json'); if (option < 0) return;
  const data = JSON.parse(fs.readFileSync(process.argv[option + 1], 'utf8'));
  const t = mount({ data }); await settle();
  assert.equal(t.$('#dashboard').hidden, false, 'Generated audit loads');
  assert.equal(t.rows().length, Math.min(5,data.tickets.length));
  for (const ticket of data.tickets) {
    t.change('#search',ticket.ticket_key,'input');
    while(!t.$(`button[data-key="${ticket.ticket_key}"]`)){const next=t.$('#ticket-pages-top button:last-child');assert.equal(next.disabled,false);next.click()}
    t.$(`button[data-key="${ticket.ticket_key}"]`).click();
    assert.equal(t.$('#detail .timeline')?.children.length || 0, ticket.history?.length || 0);
  }
  assert.equal(t.errors.length, 0); t.dom.window.close();
}
async function paginationAndTitleNormalization(width) {
  const data=clone(fixture);data.tickets=Array.from({length:12},(_,i)=>ticket(`PRSG-${i+20}`,{title:`PRSG-${i+20} · PRSG-${i+20} — Title ${i+20}`,description:'Pagination fixture',history:[{commit:commit('a',`PRSG-${i+20} Original repeated subject PRSG-${i+20}`),kind:'delivery_commit',paths:[]}]}));
  const t=mount({width,data});await settle();
  assert.deepEqual(t.rows(),['PRSG-31','PRSG-30','PRSG-29','PRSG-28','PRSG-27']);
  assert.equal(t.$('button[data-key="PRSG-29"]').closest('tr').children[1].textContent,'Title 29');
  t.$('button[data-key="PRSG-29"]').click();assert.equal(t.$('#detail-title').textContent,'PRSG-29 · Title 29');
  assert.match(t.$('.timeline').textContent,/PRSG-29 Original repeated subject PRSG-29/);
  assert.equal(t.w.normalizeTitle('PRSG-290 · Other','PRSG-29'),'PRSG-290 · Other');
  assert.equal(t.w.normalizeTitle('Mentions PRSG-29','PRSG-29'),'Mentions PRSG-29');
  assert.match(t.$('#result-count').textContent,/12 of 12 tickets.*showing 1–5/);
  const top=t.$('#ticket-pages-top');assert.equal(top.getAttribute('aria-label'),'Ticket pages above results');
  assert.equal(top.firstChild.disabled,true);assert.equal(top.querySelector('[aria-current="page"]').textContent,'1');
  assert.ok([...top.querySelectorAll('button')].every(button=>button.getAttribute('aria-controls')==='ticket-rows'));
  top.lastChild.click();assert.deepEqual(t.rows(),['PRSG-26','PRSG-25','PRSG-24','PRSG-23','PRSG-22']);
  assert.equal(t.w.document.activeElement.textContent,'2');assert.match(t.$('#result-count').textContent,/showing 6–10/);
  const csv=t.w.filteredCsv();assert.equal(csv.trim().split('\r\n').length,13);assert.match(csv,/'?Title 31/);assert.match(csv,/Title 20/);
  t.$('#ticket-pages-bottom button:last-child').click();assert.deepEqual(t.rows(),['PRSG-21','PRSG-20']);
  assert.equal(t.$('#ticket-pages-bottom button:last-child').disabled,true);
  t.change('#search','Title 31','input');assert.deepEqual(t.rows(),['PRSG-31']);assert.match(t.$('#result-count').textContent,/showing 1–1/);
  assert.equal(t.$('#ticket-pages-top').hidden,true);
  t.$('#reset').click();t.$('#ticket-pages-top button:last-child').click();
  t.change('#order','asc');assert.deepEqual(t.rows(),['PRSG-20','PRSG-21','PRSG-22','PRSG-23','PRSG-24']);
  t.$('#ticket-pages-top button:last-child').click();t.change('#owner-filter','Engineer');assert.equal(t.$('#ticket-pages-top [aria-current="page"]').textContent,'1');
  t.w.eval('currentPage=99;renderResults()');assert.equal(t.$('#ticket-pages-top [aria-current="page"]').textContent,'3');
  t.change('#search','nonexistent','input');assert.equal(t.rows().length,0);assert.equal(t.$('#export').disabled,true);assert.equal(t.$('#ticket-pages-top').hidden,true);
  t.$('#reset').click();assert.equal(t.$('#order').value,'desc');assert.deepEqual(t.rows(),['PRSG-31','PRSG-30','PRSG-29','PRSG-28','PRSG-27']);
  assert.equal(t.errors.length,0);t.dom.window.close();
}
if (process.argv.includes('--write-browser-fixture')) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'praesagus-ticket-fixture-'));
  fs.mkdirSync(path.join(dir, 'tickets')); fs.writeFileSync(path.join(dir, 'tickets/index.html'), html); fs.writeFileSync(path.join(dir, 'tickets/audit.json'), JSON.stringify(inconsistentFixture(), null, 2)); console.log(dir);
} else (async () => { landingChecks(); await paginationAndTitleNormalization(1280); await paginationAndTitleNormalization(390); await controls(1280); await controls(390); await safetyAndCsv(); await loadingAndFailure(); await inconsistentAndRecovery(); await historicalSpecification(); await decisionOverviewAndDisclosures(1280); await decisionOverviewAndDisclosures(390); await decisionFallbackAndSafety(); await generatedAudit(); console.log('Ticket dashboard DOM checks passed: search, all filters/sorts, committed evidence timeline, completion/activity separation, safe links/text, CSV neutralization/export, loading/error/empty, inconsistent checkpoints and recovery, normalized titles, full overview and five-ticket pagination with all-filtered CSV.'); })().catch(error => { console.error(error); process.exitCode = 1; });
