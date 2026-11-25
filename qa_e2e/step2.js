const { chromium } = require('playwright');
const S = __dirname, B = 'http://localhost:3101', A = 'http://localhost:8000/api/v1';
const sh = (n) => `${S}/shots/${n}.png`; const step = (m) => console.log('•', m);
const j = async (m, u, b, t) => { const r = await fetch(A + u, { method: m, headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + t }, body: b ? JSON.stringify(b) : undefined }); const x = await r.text(); if (!r.ok) throw new Error(m + u + ' ' + r.status + x.slice(0, 300)); return x ? JSON.parse(x) : null; };
const ok = (c, m) => { if (!c) throw new Error('FAIL: ' + m); step('ok: ' + m); };
(async () => {
  const lg = await fetch(A + '/auth/token/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: 'zinger', password: 'Zinger-Pass-2026' }) }).then(r => r.json());
  const t = lg.access; if (!t) throw new Error('login ' + JSON.stringify(lg));
  const cat = await j('POST', '/catalog/categories/', { name: 'Burgers', slug: 'burgers' }, t);
  const cat2 = await j('POST', '/catalog/categories/', { name: 'Pizza', slug: 'pizza' }, t);
  const mk = (c, n, price) => j('POST', '/catalog/products/', { category: c.id, name: n, slug: n.toLowerCase().replace(/ /g, '-'), sku: n.slice(0, 3).toUpperCase() + Math.floor(Math.random() * 999), variants: [{ name: 'Regular', base_price: price }] }, t);
  const zinger = await mk(cat, 'Zinger Burger', '500'); const fries = await mk(cat, 'Fries', '200'); const pizza = await mk(cat2, 'Fajita Pizza', '1200');
  await j('POST', '/orders/tables/', { location: 1, table_number: 'T-1', capacity: 4 }, t);
  await j('POST', '/cash/shifts/open/', { location: 1, opening_cash: '1000' }, t);

  const br = await chromium.launch();
  const ctx = await br.newContext({ viewport: { width: 1280, height: 800 } });
  const p = await ctx.newPage(); const errs = [];
  p.on('pageerror', e => errs.push(String(e)));
  await p.goto(B + '/login'); await p.getByLabel(/Username/i).fill('zinger'); await p.getByLabel('Password', { exact: true }).fill('Zinger-Pass-2026');
  await p.getByRole('button', { name: /sign in|log in/i }).click(); await p.waitForURL(/setup|dashboard|pos/, { timeout: 15000 });

  // --- images + deal via UI ---
  await p.goto(B + '/setup'); await p.waitForTimeout(800);
  const tabs = p.getByRole('tab', { name: /menu/i }); if (await tabs.count()) await tabs.first().click(); else { const b = p.getByText(/^Menu$/).first(); if (await b.count()) await b.click(); }
  await p.waitForSelector('text=Zinger Burger');
  await p.setInputFiles(`[data-testid="img-product-${zinger.id}"]`, `${S}/zinger.png`); await p.waitForSelector('text=Picture saved');
  await p.setInputFiles(`[data-testid="img-product-${pizza.id}"]`, `${S}/pizza.png`); await p.waitForTimeout(1200);
  const zz = await j('GET', `/catalog/products/${zinger.id}/`, null, t); ok(zz.image && zz.image.includes('/media/'), 'product image saved on server: ' + zz.image);
  await p.getByTestId('new-deal').click();
  await p.getByLabel('Deal name').fill('Zinger Combo');
  const opts = await p.locator('select[aria-label="Dish"]').first().locator('option').allTextContents(); step('dish options: ' + opts.join(' | '));
  await p.locator('select[aria-label="Dish"]').first().selectOption({ index: opts.findIndex(o => o.startsWith('Zinger')) });
  await p.getByText('+ Add another dish').click();
  await p.locator('select[aria-label="Dish"]').nth(1).selectOption({ index: opts.findIndex(o => o.startsWith('Fries')) });
  await p.getByLabel('Amount (PKR)').fill('100');
  await p.screenshot({ path: sh('10-deal-form') });
  await p.getByTestId('save-deal').click(); await p.waitForSelector('text=Deal created');
  const deals = await j('GET', '/catalog/deals/?active=false', null, t); const deal = deals.results[0]; ok(deal && deal.items.length === 2, 'deal created with 2 items');
  await p.setInputFiles(`[data-testid="img-deal-${deal.id}"]`, `${S}/combo.png`); await p.waitForSelector('text=Picture saved');
  await p.waitForTimeout(500); await p.screenshot({ path: sh('11-menu-images'), fullPage: true });

  // --- POS online ---
  await p.goto(B + '/pos'); await p.waitForSelector(`[data-testid="tile-${zinger.variants?.[0]?.id ?? ''}"], [data-testid^="tile-"]`);
  await p.waitForTimeout(1200); await p.screenshot({ path: sh('12-pos-online') });
  ok(await p.locator('[data-testid^="deal-"]').count() === 1, 'deal tile visible in POS');
  const imgs = await p.locator('main img').count(); ok(imgs >= 3, `POS shows pictures (${imgs})`);
  await p.locator('[data-testid^="tile-"]').first().click();
  await p.getByTestId(/deal-/).first().click().catch(async () => { await p.locator('[data-testid^="deal-"]').first().click(); });
  await p.getByRole('button', { name: /Send to kitchen/ }).click(); await p.waitForSelector('[data-testid="done-number"]');
  const on1 = await p.getByTestId('done-number').textContent(); ok(!on1.startsWith('OFF'), 'online order got server number ' + on1);
  await p.screenshot({ path: sh('13-order-sent') });
  const o1 = await j('GET', '/orders/?page_size=50', null, t); const ord = o1.results[0];
  // deal: 500+200 =700, -100 deal, tax 10% on 700 = 70 → plus item; check discount
  step('server order total ' + ord.total_amount + ' discount ' + ord.discount + ' items ' + ord.items.length);
  await p.keyboard.press('Escape'); await p.getByRole('button', { name: /Pay later|Done/ }).first().click().catch(() => {});

  // --- OFFLINE ---
  await p.goto(B + '/pos'); await p.waitForSelector('[data-testid^="tile-"]'); await p.waitForTimeout(800);
  await ctx.setOffline(true); step('network OFF');
  for (let i = 0; i < 2; i++) {
    await p.locator('[data-testid^="tile-"]').nth(i).click();
    await p.getByRole('button', { name: /Send to kitchen|Save order/ }).click(); await p.waitForSelector('[data-testid="done-number"]', { timeout: 20000 });
    const n = await p.getByTestId('done-number').textContent(); ok(n.startsWith('OFF-'), `offline order ${i + 1} saved locally as ${n}`);
    if (i === 0) { await p.screenshot({ path: sh('14-offline-saved') });
      await p.getByRole('button', { name: /Take payment/ }).click(); await p.getByLabel('Cash received').fill('2000'); await p.screenshot({ path: sh('15-offline-pay') });
      await p.getByRole('button', { name: /^Receive/ }).click(); await p.waitForSelector('text=Payment recorded'); await p.getByRole('button', { name: 'Done' }).click(); }
    else await p.getByRole('button', { name: 'Done' }).click();
  }
  // Dine-in offline
  await p.getByRole('button', { name: 'Dine-in', exact: true }).click().catch(() => {});
  await p.screenshot({ path: sh('16-offline-bar') });
  await p.reload().catch(() => {}); await p.waitForTimeout(1500);
  step('reload while offline → page: ' + (await p.title()) + ' / tiles ' + await p.locator('[data-testid^="tile-"]').count());
  await p.screenshot({ path: sh('17-offline-reload') });
  const before = (await j('GET', '/orders/?page_size=100', null, t)).count; 
  await ctx.setOffline(false); step('network ON');
  await p.goto(B + '/orders'); await p.waitForTimeout(500);
  for (let i = 0; i < 30; i++) { const c = (await j('GET', '/orders/?page_size=100', null, t)).count; if (c >= before + 2) break; await p.waitForTimeout(1000); }
  const after = await j('GET', '/orders/?page_size=100', null, t);
  ok(after.count === before + 2, `2 offline orders synced exactly once (${before} → ${after.count})`);
  const offs = after.results.filter(o => o.is_offline); ok(offs.length === 2, 'orders flagged is_offline');
  const paid = offs.filter(o => o.payment_status === 'PAID'); ok(paid.length === 1, 'offline payment recorded on the first order');
  await p.waitForTimeout(1500); await p.screenshot({ path: sh('18-orders-synced') });
  ok(await p.getByTestId('outbox-strip').count() === 0, 'outbox strip gone after sync');
  // Mobile
  const m = await br.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true }); const mp = await m.newPage();
  await mp.goto(B + '/login'); await mp.getByLabel(/Username/i).fill('zinger'); await mp.getByLabel('Password', { exact: true }).fill('Zinger-Pass-2026');
  await mp.getByRole('button', { name: /sign in|log in/i }).click(); await mp.waitForURL(/setup|dashboard|pos/); await mp.goto(B + '/pos'); await mp.waitForSelector('[data-testid^="tile-"]'); await mp.waitForTimeout(800);
  await mp.screenshot({ path: sh('19-pos-mobile') });
  console.log('page errors:', errs.length ? errs : 'none');
  await br.close();
})().catch(e => { console.log('ERR', e.message); process.exit(1); });
