const { chromium } = require('playwright'); const fs = require('fs');
const S = __dirname, B = 'http://localhost:3101', A = 'http://localhost:8000/api/v1';
const sh = (n) => `${S}/shots/${n}.png`; const step = (m) => console.log('•', m);
const ok = (c, m) => { if (!c) throw new Error('FAIL: ' + m); step('ok: ' + m); };
(async () => {
  const lg = await (await fetch(A + '/auth/token/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: 'zinger', password: 'Zinger-Pass-2026' }) })).json();
  const j = async (m, u, b) => { const r = await fetch(A + u, { method: m, headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + lg.access }, body: b ? JSON.stringify(b) : undefined }); const x = await r.text(); if (!r.ok) throw new Error(m + u + ' ' + r.status + x.slice(0, 300)); return x ? JSON.parse(x) : null; };
  const cat = await j('POST', '/catalog/categories/', { name: 'Burgers', slug: 'burgers' });
  await j('POST', '/catalog/products/', { category: cat.id, name: 'Zinger Burger', slug: 'zinger', sku: 'ZNG1', variants: [{ name: 'Regular', base_price: '500' }] });
  await j('POST', '/cash/shifts/open/', { location: 1, opening_cash: '500' });
  await j('PATCH', '/loyalty/settings/', { enabled: true, spend_per_point: '10', point_value: '1', min_redeem: 100 });
  const br = await chromium.launch(); const ctx = await br.newContext({ viewport: { width: 1280, height: 900 } }); const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto(B + '/login'); await p.getByLabel(/Username/i).fill('zinger'); await p.getByLabel('Password', { exact: true }).fill('Zinger-Pass-2026'); await p.getByRole('button', { name: /sign in|log in/i }).click(); await p.waitForURL(/setup|dashboard|pos/);
  const sale = async (qty) => {
    await p.goto(B + '/pos'); await p.waitForSelector('[data-testid^="tile-"]');
    for (let i = 0; i < qty; i++) await p.locator('[data-testid^="tile-"]').first().click();
    await p.getByTestId('cust-name').fill('Bilal'); await p.getByTestId('cust-phone').fill('03215550000');
  };
  // sale 1: new customer, with email, pay in full => earns points
  await sale(3); await p.waitForTimeout(700);
  ok(await p.getByTestId('cust-new').count() === 1, 'new phone is shown as a new customer');
  await p.getByTestId('cust-email').fill('bilal@example.com'); await p.screenshot({ path: sh('90-pos-customer') });
  await p.getByRole('button', { name: /Send to kitchen|Save order/ }).click(); await p.waitForSelector('[data-testid="done-number"]');
  await p.getByRole('button', { name: /Take payment/ }).click(); await p.getByLabel('Cash received').fill('5000'); await p.getByRole('button', { name: /^Receive/ }).click(); await p.waitForSelector('text=Paid in full');
  await p.getByRole('button', { name: 'Done' }).click();
  await p.waitForTimeout(800);
  let lk = await j('GET', '/loyalty/lookup/?location=1&phone=03215550000'); ok(lk.found && lk.balance >= 100 && lk.email === 'bilal@example.com', `customer saved with email, balance ${lk.balance}`);
  ok(/bilal@example\.com/.test(fs.readFileSync(S + '/backend.log', 'utf8')), 'points email sent');
  // sale 2: returning customer is recognised and can use points in the pay modal
  await sale(2); await p.waitForSelector('[data-testid=cust-known]'); ok(new RegExp(String(lk.balance)).test(await p.getByTestId('cust-known').innerText()), 'returning customer shows their points balance');
  await p.getByRole('button', { name: /Send to kitchen|Save order/ }).click(); await p.waitForSelector('[data-testid="done-number"]');
  await p.getByRole('button', { name: /Take payment/ }).click(); await p.waitForSelector('[data-testid=loyalty-panel]'); await p.screenshot({ path: sh('91-pay-points') });
  await p.getByTestId('use-points').fill('100'); await p.getByTestId('use-points-btn').click(); await p.waitForSelector('[data-testid=loy-used]');
  ok(/100/.test(await p.getByTestId('loy-used').innerText()), 'using 100 points shows the discount in the pay modal');
  await p.screenshot({ path: sh('92-pay-points-used') });
  ok(errs.length === 0, 'no page errors ' + errs.join('|'));
  await br.close(); console.log('STEP9 E2E PASSED');
})().catch(e => { console.error(e); process.exit(1); });
