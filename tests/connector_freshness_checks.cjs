/* Offline React replay using the existing external catalyst renderer; no installs. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createRequire } = require('node:module');
const project = path.resolve(__dirname, '..');
const local = createRequire(path.join(project, 'frontend/package.json'));
const external = createRequire(path.join(process.env.CATALYST_TEST_DEPS || '/tmp/praesagus-catalyst-test-deps', 'package.json'));
const React = external('react');
const { create, act } = external('react-test-renderer');
const calls = [];
globalThis.__freshness = signal => new Promise((resolve, reject) => calls.push({ signal, resolve, reject }));
const response = (state = 'succeeded') => ({ read_at: '2026-10-05T12:00:00Z', datasets: [{
  dataset: 'filings', instrumented: true, ledger: 'present', invocation_state: state,
  freshness: 'recent', last_success: '2026-10-05T11:00:00Z',
  last_attempt: { started_at: '2026-10-05T12:00:00Z', finished_at: '2026-10-05T12:01:00Z', state, yielded: 0, stored: 0, error_code: state === 'failed' ? 'fetch-failed' : null },
  data: { state: 'empty', latest_data_time: null, time_precision: 'unknown', future_times: 0, invalid_times: 0 }, coverage_warning: 'Coverage unknown',
}] });
const settle = async (call, value, failed = false) => act(async () => { failed ? call.reject(value) : call.resolve(value); await Promise.resolve(); });
(async () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'freshness-react-'));
  try {
    const output = path.join(temp, 'pages.cjs');
    await local('esbuild').build({ stdin: { contents: `export {FinancialFreshness} from '${path.join(project, 'frontend/src/pages/Financial.tsx')}'; export {default as Platforms} from '${path.join(project, 'frontend/src/pages/Platforms.tsx')}'; export {default as Pipeline} from '${path.join(project, 'frontend/src/pages/Pipeline.tsx')}';`, resolveDir: project }, outfile: output,
      platform: 'node', format: 'cjs', bundle: true, loader: { '.css': 'empty' }, plugins: [
        { name: 'react', setup(b) { b.onResolve({ filter: /^react$/ }, () => ({ path: external.resolve('react'), external: true })); } },
        { name: 'api', setup(b) {
          b.onResolve({ filter: /services\/api$/ }, () => ({ path: 'api', namespace: 'fixture' }));
          b.onLoad({ filter: /.*/, namespace: 'fixture' }, () => ({ contents: `export const fetchFinancialFreshness=(signal)=>globalThis.__freshness(signal); export const fetchPlatforms=async()=>({platforms:[{name:'edgar',label:'Edgar',status:'Configured',items_ingested:'n/a'}]}); export const fetchPipeline=async()=>({pipeline:{health:'unknown',updated_at:'inspection',dags:[{dag_id:'ingest_edgar',status:'configured',next_run:null}]}}); export const fetchFinancialCatalysts=()=>Promise.resolve({}); export const fetchFinancialCalendar=()=>{}; export const fetchFinancialFilings=()=>{}; export const fetchFinancialInsiderTrades=()=>{}; export const fetchFinancialNews=()=>{}; export const fetchFinancialSummary=()=>{}; export const fetchMoomooNews=()=>{}; export const fetchMoomooQuotes=()=>{};` }));
        } },
      ] });
    const { FinancialFreshness, Platforms, Pipeline } = require(output);
    let ui;
    await act(async () => { ui = create(React.createElement(FinancialFreshness)); });
    const rendered = () => JSON.stringify(ui.toJSON());
    const refresh = async () => act(async () => ui.root.findByType('button').props.onClick());
    assert.match(rendered(), /Reading invocation/);
    await settle(calls[0], response());
    assert.match(rendered(), /Last success/); assert.match(rendered(), /11:00:00/);
    await refresh(); assert.doesNotMatch(rendered(), /11:00:00/);
    await settle(calls[1], response('failed'));
    assert.match(rendered(), /fetch-failed/); assert.match(rendered(), /11:00:00/);
    await refresh(); await settle(calls[2], new Error('Synthetic HTTP 503'), true);
    assert.match(rendered(), /Synthetic HTTP 503/); assert.doesNotMatch(rendered(), /11:00:00/);
    await refresh(); const old = calls[3]; await refresh(); assert.equal(old.signal.aborted, true);
    await settle(old, response()); assert.doesNotMatch(rendered(), /11:00:00/);
    await settle(calls[4], { ...response(), datasets: [{ ...response().datasets[0], instrumented: false, ledger: 'uninstrumented', invocation_state: 'unknown', last_attempt: null, last_success: null }] });
    assert.match(rendered(), /uninstrumented/); assert.doesNotMatch(rendered(), /11:00:00/);
    await act(async () => ui.unmount()); assert.equal(calls[4].signal.aborted, true);
    for (const Page of [Platforms, Pipeline]) {
      let page; await act(async () => { page = create(React.createElement(Page)); });
      const text = JSON.stringify(page.toJSON());
      assert.doesNotMatch(text, /Healthy|scheduled|next run inspection/);
      assert.match(text, /Configured|configured/);
      await act(async () => page.unmount());
    }
    console.log('Freshness replay passed: empty/success, failed attempt with retained success, HTTP error clears status, stale response/unmount, uninstrumented/generic labels.');
  } finally { delete globalThis.__freshness; fs.rmSync(temp, { recursive: true, force: true }); }
})().catch(error => { console.error(error); process.exitCode = 1; });
