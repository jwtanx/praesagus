/* Offline source-contract regression for the Dashboard's on-demand Moomoo chart. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const dashboard = fs.readFileSync(path.join(root, 'frontend/src/pages/Dashboard.tsx'), 'utf8');
const component = fs.readFileSync(path.join(root, 'frontend/src/components/MoomooPriceTrend.tsx'), 'utf8');
const api = fs.readFileSync(path.join(root, 'frontend/src/services/api.ts'), 'utf8');

assert.match(dashboard, /import MoomooPriceTrend from '\.\.\/components\/MoomooPriceTrend'/);
assert.ok(dashboard.indexOf('<MoomooPriceTrend \/>') < dashboard.indexOf('<section className="trend-overview">'),
  'price trend is a separate Dashboard panel before signal Top trends');
assert.match(component, /Moomoo historical price trend/);
assert.match(component, /value="US\.AAPL"|useState\('US\.AAPL'\)/);
assert.match(component, /value="1M"/);
assert.match(component, /value="3M"/);
assert.match(component, /onSubmit=\{load\}/);
assert.match(component, /fetchMoomooHistory\(normalized, window\)/);
assert.doesNotMatch(component, /useEffect|setInterval|setTimeout/, 'no mount fetch or polling');
assert.match(component, /role="status"/);
assert.match(component, /role="alert"/);
assert.match(component, /No historical daily closes returned/);
assert.match(component, /OpenD is unavailable/);
assert.match(component, /US market-data entitlement/);
assert.match(component, /Historical daily close · adjusted \(QFQ\)/);
assert.match(component, /latest bar may still reflect an active session/);
assert.match(component, /Retrieved \{result\.retrieved_at\} UTC/);
assert.match(component, /points\.map\(point => `\$\{point\.x\},\$\{point\.y\}`\)/,
  'SVG series follows validated source order');
assert.match(component, /point\.date <= previous/);
assert.match(component, /point\.close <= 0/);
assert.match(api, /fetchMoomooHistory\(code: string, window: '1M' \| '3M'\)/);
assert.match(api, /\/api\/v1\/moomoo\/history\?/);
console.log('Dashboard Moomoo price-trend source contract passed (offline; no provider or browser runtime).');
