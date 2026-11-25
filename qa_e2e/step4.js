const { chromium } = require('playwright');
const S = __dirname, B = 'http://localhost:3101', A = 'http://localhost:8000/api/v1';
const sh = (n) => `${S}/shots/${n}.png`; const step = (m) => console.log('•', m);
const ok = (c, m) => { if (!c) throw new Error('FAIL: ' + m); step('ok: ' + m); };
(async () => {
  const lg = await fetch(A + '/auth/token/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: 'zinger', password: 'Zinger-Pass-2026' }) }).then(r => r.json());
  const t = lg.access;
  const j = async (m, u, b) => { const r = await fetch(A + u, { method: m, headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + t }, body: b ? JSON.stringify(b) : undefined }); const x = await r.text(); if (!r.ok) throw new Error(m + u + ' ' + r.status + x.slice(0, 300)); return x ? JSON.parse(x) : null; };
  const cat = await j('POST', '/catalog/categories/', { name: 'Burgers', slug: 'burgers' }); const cat2 = await j('POST', '/catalog/categories/', { name: 'Pizza', slug: 'pizza' });
  const mk = (c, n, price) => j('POST', '/catalog/products/', { category: c.id, name: n, slug: n.toLowerCase().replace(/ /g, '-'), sku: n.slice(0, 3).toUpperCase() + Math.floor(Math.random() * 999), variants: [{ name: 'Regular', base_price: price }] });
  const zinger = await mk(cat, 'Zinger Burger', '500'); const fries = await mk(cat, 'Fries', '200'); const pizza = await mk(cat2, 'Fajita Pizza', '1200'); await mk(cat2, 'Chicken Tikka Pizza', '1350'); await mk(cat, 'Beef Smash Burger', '650');
  const gf = await j('POST', '/orders/floors/', { location: 1, name: 'Ground Floor', level: 0 }); await j('POST', '/orders/floors/', { location: 1, name: 'Rooftop', level: 1 });
  await j('POST', '/cash/shifts/open/', { location: 1, opening_cash: '1000' });

  const br = await chromium.launch(); const ctx = await br.newContext({ viewport: { width: 1280, height: 900 } }); const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto(B + '/login'); await p.getByLabel(/Username/i).fill('zinger'); await p.getByLabel('Password', { exact: true }).fill('Zinger-Pass-2026');
  await p.getByRole('button', { name: /sign in|log in/i }).click(); await p.waitForURL(/setup|dashboard|pos/);

  // images for menu
  for (const [pr, f] of [[zinger, 'zinger'], [pizza, 'pizza']]) await fetch(A + `/catalog/images/product/${pr.id}/`, { method: 'POST', headers: { Authorization: 'Bearer ' + t }, body: (() => { const fd = new FormData(); fd.append('image', new Blob([require('fs').readFileSync(`${S}/${f}.png`)], { type: 'image/png' }), f + '.png'); return fd; })() });

  // --- tables via UI: add one of each shape ---
  await p.goto(B + '/setup'); await p.waitForTimeout(600);
  const tab = p.getByText('Floors & tables').first(); await tab.click(); await p.waitForSelector('text=Ground Floor');
  const addOn = async (floorIdx, shape, seats, count = 1) => {
    const card = p.locator('div.p-6').filter({ hasText: /Add tables/ }).nth(floorIdx);
    await card.getByTestId(`shape-${shape}`).click(); await card.getByLabel('Seats each').fill(String(seats)); await card.getByLabel('How many').fill(String(count));
    await card.getByTestId('add-tables').click(); await p.waitForTimeout(900);
  };
  await addOn(0, 'SQUARE', 4, 2); await addOn(0, 'ROUND', 6); await addOn(0, 'LONG', 8); await addOn(0, 'WALL', 3); await addOn(1, 'ROUND', 4, 2);
  await p.screenshot({ path: sh('20-setup-tables'), fullPage: true });
  const tb = await j('GET', '/orders/tables/'); const list = tb.results ?? tb; ok(list.length === 7, '7 tables created'); ok(new Set(list.map(x => x.shape)).size === 4, 'all 4 shapes saved: ' + [...new Set(list.map(x => x.shape))]);
  // edit table via modal
  await p.locator('svg[role=img]').first().click(); await p.locator('[role=dialog]').getByLabel('Seats', { exact: true }).fill('5'); await p.locator('[role=dialog]').getByRole('button', { name: 'Save', exact: true }).click(); await p.waitForTimeout(800);
  ok((await j('GET', '/orders/tables/')).results.some(x => x.capacity === 5), 'table seats edited in UI');

  // --- branding via UI ---
  await p.goto(B + '/setup'); await p.getByText('Tax, service charge, stock rules').first().click(); await p.waitForSelector('text=Bill & payment details');
  await p.setInputFiles('[data-testid=logo-input]', `${S}/logo.png`); await p.waitForSelector('text=Logo saved');
  await p.setInputFiles('[data-testid=qr-input]', `${S}/qr.png`); await p.waitForSelector('text=QR saved');
  for (const [i, v] of [['JazzCash', 'Zinger House', '0300 1234567'], ['Meezan Bank', 'Zinger House Pvt Ltd', 'PK36 MEZN 0001 2345 6789 01']].entries()) {
    await p.getByTestId('add-account').click(); const row = p.getByTestId(`acc-${i}`); await row.getByLabel('Bank or wallet').fill(v[0]); await row.getByLabel('Account title').fill(v[1]); await row.getByLabel('Account number').fill(v[2]);
  }
  await p.getByLabel('Line at the bottom of the bill').fill('Shukriya! Dobara tashreef layein.');
  await p.getByTestId('save-branding').click(); await p.waitForSelector('text=Bill settings saved');
  const br2 = await j('GET', '/organizations/me/branding/'); ok(br2.logo_bw.startsWith('data:image/png') && br2.qr_bw && br2.accounts.length === 2, 'branding saved: logo_bw, qr_bw, 2 accounts');
  await p.screenshot({ path: sh('21-branding'), fullPage: true });

  // --- tables page ---
  await p.goto(B + '/tables'); await p.waitForSelector('[data-testid=floor-plan] svg'); await p.waitForTimeout(500); await p.screenshot({ path: sh('22-floor-plan') });

  // --- POS: choose table on the floor plan, dine in order ---
  await p.goto(B + '/pos'); await p.waitForSelector('[data-testid^="tile-"]'); await p.waitForTimeout(800); await p.screenshot({ path: sh('23-pos-cards') });
  await p.locator('[data-testid^="tile-"]').first().click();
  await p.getByRole('button', { name: 'Dine-in', exact: true }).click(); await p.getByTestId('choose-table').click(); await p.waitForSelector('text=Choose a table'); await p.waitForTimeout(400); await p.screenshot({ path: sh('24-table-picker') });
  await p.locator('[role=dialog] svg[role=img]').nth(1).click();
  const w = await p.locator('select').first().selectOption({ index: 1 }).catch(() => null);
  await p.getByRole('button', { name: /Send to kitchen/ }).click(); await p.waitForSelector('[data-testid="done-number"]', { timeout: 15000 });
  ok(true, 'dine-in order placed with table picked on floor plan');
  // print bill popup
  const [pop] = await Promise.all([p.waitForEvent('popup'), p.getByRole('button', { name: 'Print bill' }).click()]);
  await pop.waitForSelector('img.qr', { timeout: 8000 }); const html = await pop.content();
  ok(html.includes('class="logo"') && html.includes('Zinger House') , 'bill has logo + restaurant name at top');
  ok(html.includes('0300 1234567') && html.includes('PK36 MEZN') && html.includes('Payment QR'), 'bill has account numbers and QR at bottom');
  ok(html.includes('Table T-'), 'bill shows table number');
  await pop.evaluate(() => { window.print = () => {}; window.close = () => {}; }); await pop.setViewportSize({ width: 380, height: 900 }); await pop.screenshot({ path: sh('25-bill'), fullPage: true });
  console.log('page errors:', errs.length ? errs : 'none'); await br.close();
})().catch(e => { console.log('ERR', e.message); process.exit(1); });
