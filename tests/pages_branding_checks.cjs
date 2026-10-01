const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const pages = ['artifacts/index.html', 'artifacts/tickets/index.html', 'artifacts/daily-market-brief/index.html'];
for (const file of pages) {
  const html = fs.readFileSync(file, 'utf8');
  const icon = html.match(/<link[^>]*rel="icon"[^>]*href="([^"]+)"/);
  assert.ok(icon, `${file} favicon`);
  assert.equal(path.normalize(path.join(path.dirname(file), icon[1])), 'artifacts/daily-market-brief/favicon.svg');
  assert.ok(fs.existsSync(path.join(path.dirname(file), icon[1])), `${file} favicon asset exists`);
}
const landing = fs.readFileSync(pages[0], 'utf8');
assert.match(landing, /\.brand\{font:750 15px\/1\.55 Inter,ui-sans-serif,system-ui/);
const tickets = fs.readFileSync(pages[1], 'utf8');
assert.match(tickets, /\.site-navigation\{position:sticky;top:0;/);
assert.match(tickets, /aria-label="Main navigation"/);
assert.match(tickets, /flex-wrap:wrap/);
assert.match(tickets, /aria-current="page">Tickets/);
const focusedSkipRules = [...tickets.matchAll(/\.skip:focus\{([^}]+)\}/g)];
assert.equal(focusedSkipRules.length, 1, 'single focused skip rule prevents conflicting overrides');
const focusedSkip = Object.fromEntries(focusedSkipRules[0][1].split(';').filter(Boolean).map(declaration=>declaration.split(':')));
assert.equal(focusedSkip.position, 'fixed');
assert.ok(Number(focusedSkip['z-index']) > 20, 'focused skip sits above sticky navigation');
assert.match(tickets, /#main,#detail\{scroll-margin-top:var\(--navigation-offset,100px\)!important\}/);
assert.match(tickets, /new ResizeObserver\(updateNavigationOffset\)\.observe\(siteNavigation\)/);
// Execute actual offset updater with synthetic desktop and wrapped-mobile heights.
const vm = require('node:vm');
const updater = tickets.match(/function updateNavigationOffset\(\)\{[\s\S]*?\n\}/)[0];
for (const height of [77, 133, 189.5]) {
  let offset;
  const context = {siteNavigation:{getBoundingClientRect:()=>({height})},document:{documentElement:{style:{setProperty:(name,value)=>{assert.equal(name,'--navigation-offset');offset=value;}}}}};
  vm.runInNewContext(`${updater};updateNavigationOffset();`, context);
  assert.equal(offset, `${Math.ceil(height)+16}px`);
}
console.log('Pages branding structural checks passed (visual browser QA still required).');
