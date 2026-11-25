const { chromium } = require('playwright'); const fs = require('fs'); const { randomUUID } = require('crypto');
const S = __dirname, B = 'http://localhost:3101', A = 'http://localhost:8000/api/v1';
const sh = (n) => `${S}/shots/${n}.png`; const step = (m) => console.log('•', m);
const ok = (c, m) => { if (!c) throw new Error('FAIL: ' + m); step('ok: ' + m); };
const lastCode = () => { const t = fs.readFileSync(S + '/backend.log', 'utf8'); const m = [...t.matchAll(/\b(\d{6})\b/g)]; return m.length ? m[m.length - 1][1] : null; };
(async () => {
  const tok = async (u, pw) => (await fetch(A + '/auth/token/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: u, password: pw }) })).json();
  const lg = await tok('zinger', 'Zinger-Pass-2026');
  const j = async (m, u, b) => { const r = await fetch(A + u, { method: m, headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + lg.access }, body: b ? JSON.stringify(b) : undefined }); const x = await r.text(); if (!r.ok) throw new Error(m + u + ' ' + r.status + x.slice(0, 300)); return x ? JSON.parse(x) : null; };
  const cat = await j('POST', '/catalog/categories/', { name: 'Burgers', slug: 'burgers' });
  const prod = await j('POST', '/catalog/products/', { category: cat.id, name: 'Zinger Burger', slug: 'zinger', sku: 'ZNG1', variants: [{ name: 'Regular', base_price: '500' }] });
  const pv = (await j('GET', `/catalog/products/${prod.id}/`)).variants[0];
  await j('POST', '/cash/shifts/open/', { location: 1, opening_cash: '500' });
  const bill = async (qty, phone, email) => (await j('POST', '/orders/sync/', { client_uuid: randomUUID(), location: 1, order_type: 'TAKEAWAY', customer_name: 'Ali Khan', customer_phone: phone, customer_email: email || '', items: [{ product_variant: pv.id, quantity: qty }] })).order;
  const total = async (o) => Number((await j('GET', `/orders/${o.id}/`)).total_amount);
  const payAll = async (o) => j('POST', `/cash/orders/${o.id}/payments/`, { method: 'CASH', amount: String(await total(o)) });
  const br = await chromium.launch(); const ctx = await br.newContext({ viewport: { width: 1280, height: 900 } }); const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(String(e)));
  const login = async (pg, u, pw) => { await pg.goto(B + '/login'); await pg.getByLabel(/Username/i).fill(u); await pg.getByLabel('Password', { exact: true }).fill(pw); await pg.getByRole('button', { name: /sign in|log in/i }).click(); await pg.waitForURL(/setup|dashboard|pos/); };
  await login(p, 'zinger', 'Zinger-Pass-2026');

  // ---- owner sets the loyalty rules
  await p.goto(B + '/setup'); await p.waitForSelector('[data-testid=loyalty-card]');
  await p.getByRole('switch', { name: /Loyalty points/i }).click();
  await p.getByTestId('loy-spend').fill('100'); await p.getByTestId('loy-value').fill('1');
  ok(/100 points/.test(await p.getByTestId('loy-preview').innerText()) && /min|100/.test(await p.getByTestId('loy-min').inputValue()), 'live example shows points per 1,000 and min 100 default');
  await p.screenshot({ path: sh('80-loyalty-settings') });
  await p.getByTestId('loy-save').click(); await p.waitForTimeout(1200);
  const st = await j('GET', '/loyalty/settings/'); ok(st.enabled && Number(st.spend_per_point) === 100 && st.min_redeem === 100, 'rules saved on the server (min redeem 100)');

  // ---- earn: bill of 1,000 => 10 points ... use a big one: 10 x 500 = 5,000 => 50 pts; two bills to pass 100
  const o1 = await bill(10, '03001112222', 'ali.customer@example.com'); await payAll(o1);
  let lk = await j('GET', '/loyalty/lookup/?location=1&phone=03001112222'); let exp = Math.floor(await total(o1) / 100); ok(lk.balance === exp && exp >= 50, `paid bill earns 1 point per 100 of the total (${exp} points) ` + JSON.stringify(lk).slice(0, 120));
  const mails = fs.readFileSync(S + '/backend.log', 'utf8'); ok(/ali\.customer@example\.com/.test(mails), 'points email went to the customer');
  // below minimum: redeem is refused
  const o2 = await bill(2, '03001112222'); let r = await fetch(A + `/orders/${o2.id}/redeem-points/`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + lg.access }, body: JSON.stringify({ points: 50 }) });
  ok(r.status === 400, 'cannot use points below 100 (got ' + r.status + ')'); await payAll(o2); exp += Math.floor(await total(o2) / 100);
  const o3 = await bill(10, '03001112222'); await payAll(o3); exp += Math.floor(await total(o3) / 100);
  lk = await j('GET', '/loyalty/lookup/?location=1&phone=03001112222'); ok(lk.balance === exp && exp >= 100 && lk.can_redeem, `balance is ${exp} and can now be used ` + JSON.stringify(lk).slice(0, 120));
  const o4 = await bill(4, '03001112222'); const before = await total(o4);
  await j('POST', `/orders/${o4.id}/redeem-points/`, { points: 100 }); const after = await total(o4);
  ok(before - after === 100, `100 points took Rs 100 off the bill (${before} -> ${after})`);

  // ---- UI: pay modal shows loyalty, receipt prints points + description
  await p.goto(B + '/orders'); await p.waitForSelector(`text=${o4.order_number}`);
  await payAll(o4); await p.reload(); await p.waitForSelector(`text=${o4.order_number}`);
  const [pop] = await Promise.all([p.waitForEvent('popup'), p.getByRole('button', { name: 'Print bill' }).first().click()]);
  await pop.waitForLoadState(); const rt = await pop.innerText('body');
  ok(/LOYALTY POINTS/.test(rt) && /Earn 1 point for every/i.test(rt) && /Use points when you have 100\+/.test(rt) && /Points used/.test(rt), 'printed bill shows points and a short simple-English description');
  await pop.screenshot({ path: sh('81-receipt-loyalty') }); await pop.close();

  // ---- customers page
  await p.goto(B + '/customers'); await p.waitForSelector('[data-testid^=cust-]');
  ok(/Ali Khan/.test(await p.locator('main').innerText()) && /03001112222/.test(await p.locator('main').innerText()), 'customers page lists the customer with phone');
  await p.screenshot({ path: sh('82-customers') });
  const [dl] = await Promise.all([p.waitForEvent('download'), p.getByTestId('csv-cust').click()]); ok(/Points/.test(fs.readFileSync(await dl.path(), 'utf8')), 'customers CSV downloads');

  // ---- reminders
  await p.goto(B + '/setup'); await p.waitForSelector('[data-testid=loy-remind]'); await p.getByTestId('loy-remind').click(); await p.waitForTimeout(1200);
  ok(/Reminder sent|No one needs/.test(await p.locator('body').innerText()), 'send-reminders button reports a result');
  await p.screenshot({ path: sh('83-reminders') });

  // ---- email: add + verify in My account
  await p.getByTestId('account-btn').click(); await p.getByTestId('em-new').fill('owner@zinger.pk'); await p.getByTestId('em-pw').fill('Zinger-Pass-2026');
  ok(await p.getByTestId('em-send').isEnabled(), 'send code enabled once email and password are filled');
  await p.getByTestId('em-send').click(); await p.waitForSelector('[data-testid=em-code]'); await p.waitForTimeout(600);
  const c1 = lastCode(); ok(!!c1, 'verification code was emailed (' + c1 + ')');
  await p.getByTestId('em-code').fill('000000'); await p.getByTestId('em-confirm').click(); await p.waitForTimeout(700);
  ok(await p.getByTestId('em-code').count() === 1, 'wrong code does not confirm');
  await p.getByTestId('em-code').fill(c1); await p.getByTestId('em-confirm').click(); await p.waitForTimeout(1200);
  await p.screenshot({ path: sh('84-email-verified') });
  ok((await j('GET', '/auth/me/')).email === 'owner@zinger.pk', 'email saved after the code is confirmed');

  // ---- forgot password (fresh browser, signed out)
  const f = await br.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true }); const fp = await f.newPage(); fp.on('pageerror', e => errs.push(String(e)));
  await fp.goto(B + '/login'); await fp.getByTestId('forgot-link').click(); await fp.waitForURL(/forgot-password/);
  await fp.screenshot({ path: sh('85-m-forgot') });
  await fp.getByTestId('fp-ident').fill('owner@zinger.pk'); await fp.getByTestId('fp-send').click(); await fp.waitForTimeout(1500);
  const c2 = lastCode(); ok(!!c2 && c2 !== c1, 'reset code emailed (' + c2 + ')');
  const inputs = fp.locator('input'); await fp.getByLabel(/6-digit code/).fill(c2); await fp.getByLabel('New password', { exact: true }).fill('Zinger-Reset-2027!'); await fp.getByLabel('New password again').fill('Zinger-Reset-2027!');
  await fp.screenshot({ path: sh('86-m-forgot-code') });
  await fp.getByTestId('fp-reset').click(); await fp.waitForTimeout(1500);
  ok(!!(await tok('zinger', 'Zinger-Reset-2027!')).access && !(await tok('zinger', 'Zinger-Pass-2026')).access, 'new password works, old one does not');
  // unknown identity gets the same neutral answer (no account enumeration)
  const g = await fetch(A + '/auth/forgot-password/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ identifier: 'nobody@nowhere.com' }) }); ok(g.status === 200, 'unknown email gets the same generic response');
  ok(errs.length === 0, 'no page errors ' + errs.join('|'));
  await br.close(); console.log('STEP8 E2E PASSED');
})().catch(e => { console.error(e); process.exit(1); });
