const { chromium } = require('playwright'); const fs = require('fs');
const S = __dirname, B = 'http://localhost:3101', A = 'http://localhost:8000/api/v1';
const sh = (n) => `${S}/shots/${n}.png`; const step = (m) => console.log('•', m);
const ok = (c, m) => { if (!c) throw new Error('FAIL: ' + m); step('ok: ' + m); };
(async () => {
  const tok = async (pw) => (await fetch(A + '/auth/token/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: 'zinger', password: pw }) })).json();
  const lg = await tok('Zinger-Pass-2026');
  const j = async (m, u, b) => { const r = await fetch(A + u, { method: m, headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + lg.access }, body: b ? JSON.stringify(b) : undefined }); const x = await r.text(); if (!r.ok) throw new Error(m + u + ' ' + r.status + x.slice(0, 300)); return x ? JSON.parse(x) : null; };
  const L = (x) => x.results ?? x;
  const cat = await j('POST', '/catalog/categories/', { name: 'Burgers', slug: 'burgers' });
  const prod = await j('POST', '/catalog/products/', { category: cat.id, name: 'Zinger Burger', slug: 'zinger', sku: 'ZNG1', variants: [{ name: 'Regular', base_price: '500' }] });
  const pv = (await j('GET', `/catalog/products/${prod.id}/`)).variants[0];
  await j('POST', '/cash/shifts/open/', { location: 1, opening_cash: '500' });
  const br = await chromium.launch(); const ctx = await br.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true }); const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto(B + '/login'); await p.getByLabel(/Username/i).fill('zinger'); await p.getByLabel('Password', { exact: true }).fill('Zinger-Pass-2026'); await p.getByRole('button', { name: /sign in|log in/i }).click(); await p.waitForURL(/setup|dashboard|pos/);

  // ---- kitchen display
  const o = await j('POST', '/orders/', { location: 1, order_type: 'TAKEAWAY' }); await j('POST', '/orders/items/', { order: o.id, product_variant: pv.id, quantity: 3, notes: 'extra spicy' });
  const num = (await j('GET', `/orders/${o.id}/`)).order_number;
  await p.goto(B + '/kitchen'); await p.waitForSelector(`[data-testid="kds-${num}"]`);
  ok(await p.getByTestId('kds-col-NEW').getByTestId(`kds-${num}`).count() === 1, 'new order shows in the New column');
  ok(/extra spicy/.test(await p.getByTestId(`kds-${num}`).innerText()) && /3×/.test(await p.getByTestId(`kds-${num}`).innerText()), 'ticket shows quantity and note');
  await p.screenshot({ path: sh('70-kitchen-new') });
  await p.getByTestId(`kds-${num}`).getByTestId('kds-advance').click(); await p.waitForSelector(`[data-testid="kds-col-PREPARING"] [data-testid="kds-${num}"]`);
  ok((await j('GET', `/orders/${o.id}/`)).status === 'PREPARING', 'Start cooking moves it to Cooking');
  await p.screenshot({ path: sh('71-kitchen-cooking') });
  await p.getByTestId(`kds-${num}`).getByTestId('kds-advance').click(); await p.waitForSelector(`[data-testid="kds-col-READY"] [data-testid="kds-${num}"]`);
  ok((await j('GET', `/orders/${o.id}/`)).status === 'READY', 'Mark ready moves it to Ready');
  // a phone view of the kitchen
  const m = await br.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true }); const mp = await m.newPage();
  await mp.goto(B + '/login'); await mp.getByLabel(/Username/i).fill('zinger'); await mp.getByLabel('Password', { exact: true }).fill('Zinger-Pass-2026'); await mp.getByRole('button', { name: /sign in|log in/i }).click(); await mp.waitForURL(/setup|dashboard|pos/);
  await mp.goto(B + '/kitchen'); await mp.waitForSelector('[data-testid=kds]'); await mp.screenshot({ path: sh('72-m-kitchen') });
  ok(await mp.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), 'kitchen fits phone width');

  // ---- CSV exports (and formula injection is neutralised)
  await j('POST', '/operations/expenses/', { location: 1, category: 'Gas', amount: '250', description: '=HYPERLINK("http://x")' });
  await p.goto(B + '/expenses'); await p.waitForSelector('[data-testid^=exp-]');
  let [dl] = await Promise.all([p.waitForEvent('download'), p.getByTestId('csv-exp').click()]); let txt = fs.readFileSync(await dl.path(), 'utf8');
  ok(txt.charCodeAt(0) === 0xFEFF && /Category/.test(txt) && /250/.test(txt), 'expenses CSV has BOM, header and amount');
  ok(/"'=HYPERLINK/.test(txt) && !/,"=HYPERLINK/.test(txt), 'formula in a note is neutralised in CSV');
  await p.goto(B + '/day-report'); await p.waitForSelector('[data-testid=z-net]');
  [dl] = await Promise.all([p.waitForEvent('download'), p.getByTestId('csv-z').click()]); txt = fs.readFileSync(await dl.path(), 'utf8');
  ok(/Net sales/.test(txt) && /Total expenses/.test(txt) && /end-of-day-\d{4}-\d{2}-\d{2}\.csv/.test(dl.suggestedFilename()), 'day report CSV downloads with totals');
  await p.goto(B + '/orders'); await p.waitForSelector(`text=${num}`);
  [dl] = await Promise.all([p.waitForEvent('download'), p.getByTestId('csv-orders').click()]); txt = fs.readFileSync(await dl.path(), 'utf8'); ok(txt.includes(num), 'orders CSV lists the order');

  // ---- change password from the account menu
  await p.getByTestId('account-btn').click(); await p.getByTestId('pw-cur').fill('Zinger-Pass-2026'); await p.getByTestId('pw-new').fill('Zinger-New-2027!'); await p.getByTestId('pw-again').fill('Zinger-New-2028!');
  ok(await p.getByTestId('pw-save').isDisabled(), 'save disabled while the two new passwords differ');
  await p.getByTestId('pw-again').fill('Zinger-New-2027!'); await p.screenshot({ path: sh('73-account') });
  await p.getByTestId('pw-save').click(); await p.waitForTimeout(1200);
  ok(!(await tok('Zinger-Pass-2026')).access && !!(await tok('Zinger-New-2027!')).access, 'old password stops working, new one logs in');
  await p.getByTestId('account-btn').click(); await p.getByTestId('pw-cur').fill('wrong-pass'); await p.getByTestId('pw-new').fill('Another-Pass-9911'); await p.getByTestId('pw-again').fill('Another-Pass-9911'); await p.getByTestId('pw-save').click(); await p.waitForTimeout(800);
  ok(await p.getByText(/current password is not correct/i).count() > 0, 'wrong current password is rejected with a clear message');
  ok(errs.length === 0, 'no page errors ' + errs.join('|'));
  await br.close(); console.log('STEP7 E2E PASSED');
})().catch(e => { console.error(e); process.exit(1); });
