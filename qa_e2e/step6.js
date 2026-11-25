const { chromium } = require('playwright');
const S = __dirname, B = 'http://localhost:3101', A = 'http://localhost:8000/api/v1';
const sh = (n) => `${S}/shots/${n}.png`; const step = (m) => console.log('•', m);
const ok = (c, m) => { if (!c) throw new Error('FAIL: ' + m); step('ok: ' + m); };
(async () => {
  const lg = await fetch(A + '/auth/token/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: 'zinger', password: 'Zinger-Pass-2026' }) }).then(r => r.json());
  const j = async (m, u, b) => { const r = await fetch(A + u, { method: m, headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + lg.access }, body: b ? JSON.stringify(b) : undefined }); const x = await r.text(); if (!r.ok) throw new Error(m + u + ' ' + r.status + x.slice(0, 300)); return x ? JSON.parse(x) : null; };
  const L = (x) => x.results ?? x;
  const cat = await j('POST', '/catalog/categories/', { name: 'Burgers', slug: 'burgers' });
  const prod = await j('POST', '/catalog/products/', { category: cat.id, name: 'Zinger Burger', slug: 'zinger', sku: 'ZNG1', variants: [{ name: 'Regular', base_price: '500' }] });
  const pv = (await j('GET', `/catalog/products/${prod.id}/`)).variants[0];
  const chicken = await j('POST', '/inventory/ingredients/', { name: 'Chicken', base_unit: 'G' });
  const fl = await j('POST', '/orders/floors/', { location: 1, name: 'Ground Floor', level: 0 });
  const t1 = await j('POST', '/orders/tables/', { floor: fl.id, location: 1, table_number: 'T-1', capacity: 4, shape: 'SQUARE' });
  const t2 = await j('POST', '/orders/tables/', { floor: fl.id, location: 1, table_number: 'T-2', capacity: 2, shape: 'ROUND' });
  const shift = await j('POST', '/cash/shifts/open/', { location: 1, opening_cash: '1000' });

  const br = await chromium.launch(); const ctx = await br.newContext({ viewport: { width: 1280, height: 900 } }); const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto(B + '/login'); await p.getByLabel(/Username/i).fill('zinger'); await p.getByLabel('Password', { exact: true }).fill('Zinger-Pass-2026');
  await p.getByRole('button', { name: /sign in|log in/i }).click(); await p.waitForURL(/setup|dashboard|pos/);
  const dlg = () => p.locator('[role=dialog]').last();

  // ---- reservations (tomorrow so the time is always in the future)
  await p.goto(B + '/reservations'); await p.waitForSelector('[data-testid=new-booking]');
  await p.getByRole('button', { name: 'Next day' }).click();
  async function book(name, party, time, tableIdx) {
    await p.getByTestId('new-booking').click(); await p.waitForSelector('[data-testid=res-name]');
    await p.getByTestId('res-name').fill(name); await p.getByTestId('res-party').fill(String(party)); await p.getByTestId('res-time').fill(time);
    await p.getByTestId('res-table').click(); await p.waitForSelector('text=Choose a table'); await dlg().locator('svg[role=img]').nth(tableIdx).click(); await p.waitForTimeout(300);
  }
  await book('Bilal', 3, '20:00', 0); await p.screenshot({ path: sh('60-booking-form') });
  await p.getByTestId('res-save').click(); await p.waitForSelector('text=Bilal'); await p.waitForTimeout(500);
  let rs = L(await j('GET', '/operations/reservations/')); ok(rs.length === 1 && rs[0].table === t1.id && rs[0].party_size === 3, 'booking saved for T-1, party of 3');
  await book('Sana', 2, '20:30', 0); await p.getByTestId('res-save').click(); await p.waitForTimeout(1200);
  rs = L(await j('GET', '/operations/reservations/')); ok(rs.length === 1, 'overlapping booking on the same table was refused');
  await p.keyboard.press('Escape'); await p.waitForTimeout(300);
  await p.getByTestId('new-booking').click().catch(() => {}); 
  await p.waitForSelector('[data-testid=res-name]'); await p.getByTestId('res-name').fill('Big'); await p.getByTestId('res-party').fill('3');
  await p.getByTestId('res-table').click(); await p.waitForSelector('text=Choose a table'); await dlg().locator('svg[role=img]').nth(1).click(); await p.waitForTimeout(500);
  ok(await p.getByText(/seats only 2/).count() > 0, 'party of 3 cannot take the 2-seat table');
  await p.keyboard.press('Escape'); await p.keyboard.press('Escape');
  await p.screenshot({ path: sh('61-reservations') });
  const rid = rs[0].id; await p.reload(); await p.getByRole('button', { name: 'Next day' }).click(); await p.waitForSelector(`[data-testid=res-${rid}]`);
  await p.getByTestId('res-seat').click(); await p.waitForTimeout(1000);
  ok(L(await j('GET', '/orders/tables/')).find(x => x.id === t1.id).status === 'OCCUPIED', 'seating a booking marks the table occupied');
  await p.goto(B + '/tables'); await p.waitForSelector('[data-testid=floor-plan]'); ok(await p.getByTestId('to-reservations').count() === 1, 'tables page links to bookings');


  // ---- drag a table on the floor plan
  await p.goto(B + '/tables'); await p.waitForSelector('[data-testid=floor-canvas]');
  await p.getByTestId('edit-layout').click(); const box = await p.getByTestId(`ft-${t2.id}`).boundingBox();
  await p.mouse.move(box.x + box.width / 2, box.y + box.height / 2); await p.mouse.down(); await p.mouse.move(box.x + box.width / 2 + 203, box.y + box.height / 2 + 97, { steps: 8 }); await p.mouse.up(); await p.waitForTimeout(800);
  let tt = L(await j('GET', '/orders/tables/')).find(x => x.id === t2.id); ok(tt.pos_x !== null && tt.pos_x % 10 === 0 && tt.pos_y % 10 === 0, `table moved and snapped to (${tt.pos_x},${tt.pos_y})`);
  await p.screenshot({ path: sh('69-rearrange') }); await p.reload(); await p.waitForSelector('[data-testid=floor-canvas]');
  const b2 = await p.getByTestId(`ft-${t2.id}`).boundingBox(); ok(Math.abs(b2.x - (box.x + 203)) < 15, 'position persists after reload');
  await p.getByTestId('edit-layout').click(); await p.getByTestId('reset-layout').click(); await p.waitForTimeout(800);
  tt = L(await j('GET', '/orders/tables/')).find(x => x.id === t2.id); ok(tt.pos_x === null, 'auto-arrange clears saved positions');

  // ---- expenses
  await p.goto(B + '/expenses'); await p.getByTestId('new-expense').click();
  await p.getByTestId('cat-Gas').click(); await p.getByTestId('exp-amount').fill('400'); await p.getByText('Taken from cash drawer').click(); await p.getByTestId('exp-save').click(); await p.waitForTimeout(1000);
  await p.getByTestId('new-expense').click(); await p.getByTestId('cat-Rent').click(); await p.getByTestId('exp-amount').fill('5000'); await p.getByTestId('exp-save').click(); await p.waitForTimeout(1000);
  ok(/5,?400/.test(await p.getByTestId('exp-total').innerText()), 'expense total shows 5,400');
  const sd = await j('GET', `/cash/shifts/${shift.id}/`); ok(Number(sd.expected_cash) === 600, 'drawer expense reduced expected cash to 600');
  await p.screenshot({ path: sh('62-expenses') });

  // ---- suppliers + purchases
  await p.goto(B + '/purchases'); await p.getByRole('tab', { name: /Suppliers/ }).click(); await p.getByTestId('new-supplier').click();
  await p.getByTestId('sup-name').fill('Al-Madina Traders'); await p.getByTestId('sup-save').click(); await p.waitForSelector('text=Al-Madina Traders');
  await p.getByRole('tab', { name: /Purchases/ }).click(); await p.getByTestId('new-purchase').click();
  await p.getByTestId('pur-supplier').selectOption({ label: 'Al-Madina Traders' }); await p.getByTestId('line-ing-0').selectOption({ label: 'Chicken' });
  await p.getByTestId('line-qty-0').fill('5'); await p.getByTestId('line-cost-0').fill('600');
  ok(/3,?000/.test(await p.getByTestId('pur-total').innerText()), 'bill total = 5 kg × 600 = 3,000');
  await p.getByTestId('pur-paid').fill('1000'); await p.screenshot({ path: sh('63-purchase-form') }); await p.getByTestId('pur-save').click(); await p.waitForSelector('[data-testid^=pur-]:has-text("Due")'); 
  const st = L(await j('GET', '/inventory/stock/')).find(x => x.ingredient === chicken.id || x.ingredient_id === chicken.id);
  ok(st && Number(st.quantity) === 5000, 'stock rose to 5000 g'); await p.screenshot({ path: sh('64-purchases') });
  await p.getByTestId('pur-pay').click(); await p.getByTestId('pay-save').click(); await p.waitForSelector('text=Paid'); 
  const pu = L(await j('GET', '/operations/purchases/'))[0]; ok(Number(pu.due) === 0, 'supplier bill fully paid');

  // ---- a sale, then the end-of-day report
  const o = await j('POST', '/orders/', { location: 1, order_type: 'TAKEAWAY' }); await j('POST', '/orders/items/', { order: o.id, product_variant: pv.id, quantity: 2 });
  const total = Number((await j('GET', `/orders/${o.id}/`)).total_amount); await j('POST', `/cash/orders/${o.id}/payments/`, { method: 'CASH', amount: String(total) });
  await p.goto(B + '/day-report'); await p.waitForSelector('[data-testid=z-net]');
  ok(Number((await p.getByTestId('z-net').innerText()).replace(/[^\d.]/g, '')) === total, `net sales = ${total}`);
  ok(/5,?400/.test(await p.getByTestId('z-exp').innerText()), 'report shows 5,400 expenses');
  const left = total - 5400 - 1000 - 2000; ok(Number((await p.getByTestId('z-left').innerText()).replace(/[^\d.-]/g, '')) === left, 'left after costs shown');
  ok(await p.getByTestId('open-shift-warning').count() === 1, 'warns that the shift is still open');
  await p.screenshot({ path: sh('65-day-report'), fullPage: true });
  const [z] = await Promise.all([ctx.waitForEvent('page'), p.getByTestId('print-z').click()]); await z.waitForLoadState(); const zt = await z.content();
  ok(/END OF DAY REPORT/.test(zt) && /NET SALES/.test(zt) && /STILL OPEN/.test(zt), 'printed Z report has the key sections'); await z.close().catch(() => {});
  const exp = await j('GET', `/cash/shifts/${shift.id}/`);
  await j('POST', `/cash/shifts/${shift.id}/close/`, { counted_cash: String(Number(exp.expected_cash)) });
  await p.reload(); await p.waitForSelector('[data-testid=z-net]'); await p.waitForTimeout(500);
  ok(await p.getByTestId('open-shift-warning').count() === 0, 'warning disappears after the shift is closed');

  // phone view
  const m = await br.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true }); const mp = await m.newPage();
  await mp.goto(B + '/login'); await mp.getByLabel(/Username/i).fill('zinger'); await mp.getByLabel('Password', { exact: true }).fill('Zinger-Pass-2026'); await mp.getByRole('button', { name: /sign in|log in/i }).click(); await mp.waitForURL(/setup|dashboard|pos/);
  for (const [path, n] of [['/reservations', '66-m-reservations'], ['/day-report', '67-m-day-report'], ['/purchases', '68-m-purchases']]) {
    await mp.goto(B + path); await mp.waitForTimeout(1500); await mp.screenshot({ path: sh(n) });
    ok(await mp.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), `${path} fits the phone width`);
  }
  ok(errs.length === 0, 'no page errors ' + errs.join('|'));
  await br.close(); console.log('STEP6 E2E PASSED');
})().catch(e => { console.error(e); process.exit(1); });
