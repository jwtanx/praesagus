/* Run after installing isolated test tools:
 * npm install --prefix /tmp/praesagus-catalyst-test-deps --no-package-lock --no-save react-test-renderer@18.3.1
 * node tests/catalyst_frontend_checks.cjs
 * Optional CATALYST_TEST_DEPS overrides that temporary directory. No project dependency changes.
 */
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const { createRequire } = require('node:module');
const project = path.resolve(__dirname, '..');
const frontendRequire = createRequire(path.join(project, 'frontend/package.json'));
const testRequire = createRequire(path.join(process.env.CATALYST_TEST_DEPS || '/tmp/praesagus-catalyst-test-deps', 'package.json'));
const React = testRequire('react');
const { create, act } = testRequire('react-test-renderer');
const esbuild = frontendRequire('esbuild');
const calls = [];
globalThis.__catalystRequests = (ticker, type, offset, signal) => new Promise((resolve, reject) => calls.push({ ticker, type, offset, signal, resolve, reject }));
const row = {
  id: 'news:1', source_id: '1', event_type: 'news', subtype: null, ticker: 'AAPL', title: 'Frozen company disclosure',
  source: 'Fixture provider', source_url: 'https://example.org/source', event_at: '2026-10-01', time_precision: 'date', timezone: null,
  published_at: '2026-10-01', available_at: null, ingested_at: null, raw_event_at: '2026-10-01', scheduled: false,
  estimated: false, data_gaps: ['available_at unavailable'],
};
const data = (records = [row], extra = {}) => ({ records, count: records.length, total: records.length, limit: 50, offset: 0,
  retrieved_at: '2026-10-01T12:00:00Z', dataset_status: { news: { status: 'loaded', rows_read: 1, rows_skipped: 0, duplicates_removed: 0 },
    filings: { status: 'unreadable' }, calendar: { status: 'absent' } }, ...extra });
const settle = async (call, value, reject = false) => act(async () => { reject ? call.reject(value) : call.resolve(value); await Promise.resolve(); });
(async () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'catalyst-react-'));
  try {
    const target = path.join(temp, 'component.cjs');
    await esbuild.build({ entryPoints: [path.join(project, 'frontend/src/components/CatalystInbox.tsx')], outfile: target,
      platform: 'node', format: 'cjs', bundle: true, loader: { '.css': 'empty' }, plugins: [
        { name: 'same-react-instance', setup(build) { build.onResolve({ filter: /^react$/ }, () => ({ path: testRequire.resolve('react'), external: true })); } },
        { name: 'offline-api', setup(build) {
          build.onResolve({ filter: /services\/api$/ }, () => ({ path: 'fixture-api', namespace: 'fixture' }));
          build.onLoad({ filter: /.*/, namespace: 'fixture' }, () => ({ contents: 'export const fetchFinancialCatalysts=(...args)=>globalThis.__catalystRequests(...args);' }));
        } },
      ] });
    const { default: Inbox, catalystSourceUrl, catalystTime, catalystWarnings } = require(target);
    for (const unsafe of ['javascript:alert(1)', 'https://user:pass@example.org', '//example.org', 'https://example.org/\nevil', 'https://example.org\\evil']) assert.equal(catalystSourceUrl(unsafe), null);
    assert.equal(catalystSourceUrl('https://example.org/source'), 'https://example.org/source');
    assert.match(catalystTime(row), /date only/);
    assert.match(catalystTime({ ...row, event_at: null }), /unavailable/);
    assert.equal(catalystWarnings(data()).length, 2);
    let tree;
    await act(async () => { tree = create(React.createElement(Inbox)); });
    const text = () => JSON.stringify(tree.toJSON());
    const button = name => tree.root.findAllByType('button').find(node => node.children.join('') === name);
    assert.match(text(), /Reading stored/);
    await settle(calls[0], data());
    assert.match(text(), /Partial dataset coverage/);
    const link = tree.root.findByType('a');
    assert.equal(link.props.href, row.source_url);
    assert.equal(link.props.rel, 'noopener noreferrer');
    assert.match(text(), /date only/);
    await act(async () => { tree.root.findByType('input').props.onChange({ target: { value: ' msft ' } }); });
    assert.doesNotMatch(text(), /Frozen company disclosure/);
    assert.match(text(), /Filters changed/);
    await act(async () => { tree.root.findByType('form').props.onSubmit({ preventDefault() {} }); });
    assert.equal(calls[1].ticker, 'MSFT');
    await act(async () => { button('Refresh').props.onClick(); });
    assert.equal(calls[1].signal.aborted, true);
    await settle(calls[1], data([{ ...row, title: 'STALE RESPONSE' }]));
    assert.doesNotMatch(text(), /STALE RESPONSE/);
    await settle(calls[2], new Error('Fixture refresh failure'), true);
    assert.match(text(), /Fixture refresh failure/);
    assert.doesNotMatch(text(), /Frozen company disclosure/);
    await act(async () => { button('Apply').props.onClick?.(); tree.root.findByType('form').props.onSubmit({ preventDefault() {} }); });
    await settle(calls[3], data([row], { total: 120 }));
    await act(async () => { button('Next').props.onClick(); });
    assert.equal(calls[4].offset, 50);
    await settle(calls[4], data([], { total: 120, offset: 50 }));
    assert.match(text(), /No matching stored evidence/);
    await act(async () => { button('Previous').props.onClick(); });
    assert.equal(calls[5].offset, 0);
    await settle(calls[5], data([{ ...row, scheduled: true, event_type: 'calendar', title: 'Scheduled event', source_url: 'javascript:evil' }]));
    assert.match(text(), /Upcoming/);
    assert.equal(tree.root.findAllByType('a').length, 0);
    await act(async () => { button('Refresh').props.onClick(); });
    await act(async () => { tree.unmount(); });
    assert.equal(calls[6].signal.aborted, true);
    await settle(calls[6], data());
    assert.equal(tree.toJSON(), null);
    console.log('Frontend checks passed: source safety, provenance, warnings, loading, apply/refresh, stale responses, paging, empty/error, unmount.');
  } finally { fs.rmSync(temp, { recursive: true, force: true }); }
})().catch(error => { console.error(error); process.exitCode = 1; });
