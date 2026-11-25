const { chromium } = require('playwright');
const S = __dirname, B = 'http://localhost:3101', A = 'http://localhost:8000/api/v1';
const sh = (n) => `${S}/shots/${n}.png`; const step = (m) => console.log('•', m);
const ok = (c, m) => { if (!c) throw new Error('FAIL: ' + m); step('ok: ' + m); };
(async () => {
  const lg = await fetch(A + '/auth/token/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: 'zinger', password: 'Zinger-Pass-2026' }) }).then(r => r.json());
  const t = lg.access;
  const j = async (m, u, b) => { const r = await fetch(A + u, { method: m, headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + t }, body: b ? JSON.stringify(b) : undefined }); const x = await r.text(); if (!r.ok) throw new Error(m + u + ' ' + r.status + x.slice(0, 300)); return x ? JSON.parse(x) : null; };
  const L = (x) => x.results ?? x;
  const cat = await j('POST', '/catalog/categories/', { name: 'Burgers', slug: 'burgers' });
  const mk = (n, price) => j('POST', '/catalog/products/', { category: cat.id, name: n, slug: n.toLowerCase().replace(/ /g, '-'), sku: n.slice(0, 3).toUpperCase() + Math.floor(Math.random() * 999), variants: [{ name: 'Regular', base_price: price }] });
  const zinger = await mk('Zinger Burger', '500'); const fries = await mk('Fries', '200'); const pizza = await mk('Fajita Pizza', '1200');
  const fl = await j('POST', '/orders/floors/', { location: 1, name: 'Ground Floor', level: 0 });
  for (const n of ['T-1', 'T-2']) await j('POST', '/orders/tables/', { floor: fl.id, location: 1, table_number: n, capacity: 4, shape: 'SQUARE' });
  await j('POST', '/cash/shifts/open/', { location: 1, opening_cash: '1000' });

  const br = await chromium.launch(); const ctx = await br.newContext({ viewport: { width: 1280, height: 900 } }); const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto(B + '/login'); await p.getByLabel(/Username/i).fill('zinger'); await p.getByLabel('Password', { exact: true }).fill('Zinger-Pass-2026');
  await p.getByRole('button', { name: /sign in|log in/i }).click(); await p.waitForURL(/setup|dashboard|pos/);

  // ---- 1. Dish options via Setup UI
  await p.goto(B + '/setup'); await p.getByText('Categories, dishes and prices').first().click(); await p.waitForSelector(`[data-testid=dish-options-${zinger.id}]`);
  await p.getByTestId(`dish-options-${zinger.id}`).click(); await p.waitForSelector('[data-testid=grp-name]');
  const d = p.locator('[role=dialog]');
  await d.getByTestId('grp-name').fill('Spice level'); await d.getByTestId('grp-required').check();
  await d.getByTestId('opt-name-0').fill('Mild'); await d.getByTestId('opt-name-1').fill('Hot');
  await d.getByTestId('grp-save').click(); await p.waitForSelector('[data-testid^=attached-]');
  await d.getByTestId('grp-name').fill('Extras'); await d.getByTestId('grp-multi').check();
  await d.getByTestId('opt-name-0').fill('Cheese'); await d.getByTestId('opt-price-0').fill('50'); await d.getByTestId('opt-name-1').fill('Egg'); await d.getByTestId('opt-price-1').fill('80');
  await p.screenshot({ path: sh('50-dish-options') });
  await d.getByTestId('grp-save').click(); await p.waitForTimeout(1200);
  const zp = await j('GET', `/catalog/products/${zinger.id}/`); ok(zp.modifier_groups.length === 2, 'two option groups attached via UI');
  ok(zp.modifier_groups.find(g => g.name === 'Spice level').required, 'Spice level is required');

  // ---- 2. POS: options modal, required enforced, notes
  await p.goto(B + '/pos'); await p.waitForSelector('[data-testid^="tile-"]');
  const fv0 = (await j('GET', `/catalog/products/${fries.id}/`)).variants[0].id; await p.getByTestId(`tile-${fv0}`).click();
  const zv = zp.variants[0].id;
  await p.getByTestId(`tile-${zv}`).click(); await p.waitForSelector('[data-testid=opt-add]');
  ok(await p.getByTestId('opt-add').isDisabled(), 'Add disabled until required group chosen');
  await p.screenshot({ path: sh('51-options-modal') });
  const g1 = zp.modifier_groups.find(g => g.name === 'Spice level'), g2 = zp.modifier_groups.find(g => g.name === 'Extras');
  await p.getByTestId(`opt-${g1.options.find(o => o.name === 'Hot').id}`).click();
  await p.getByTestId(`opt-${g2.options.find(o => o.name === 'Cheese').id}`).click(); await p.getByTestId(`opt-${g2.options.find(o => o.name === 'Egg').id}`).click();
  await p.getByTestId('opt-note').fill('no onions'); await p.locator('[role=dialog]').getByRole('button', { name: 'More', exact: true }).click();
  ok(/1,?260/.test(await p.getByTestId('opt-add').innerText()), 'modal total = (500+50+80)×2 = 1260');
  await p.getByTestId('opt-add').click();
  // fries line note
  await p.getByTestId('line-note').filter({ hasText: 'Add note' }).first().click(); await p.getByTestId('line-note-input').fill('no salt'); await p.keyboard.press('Enter');
  await p.waitForTimeout(300); await p.screenshot({ path: sh('52-pos-cart-options') });
  await p.getByTestId('auto-kot').uncheck().catch(() => {});
  await p.getByRole('button', { name: /Send to kitchen/ }).click(); await p.waitForSelector('[data-testid="done-number"]');
  const num = await p.getByTestId('done-number').innerText();
  let o = L(await j('GET', '/orders/')).find(x => x.order_number === num);
  const zi = o.items.find(i => i.product_name === 'Zinger Burger'), fi = o.items.find(i => i.product_name === 'Fries');
  ok(Number(zi.unit_price) === 630 && zi.quantity === 2 && zi.modifiers.length === 3 && zi.notes === 'no onions', 'server stored options price 630, 3 modifiers, note');
  ok(fi.notes === 'no salt', 'fries note saved');
  // ---- 3. KOT
  const [kot] = await Promise.all([ctx.waitForEvent('page'), p.getByTestId('print-kot').click()]);
  await kot.waitForLoadState(); const kt = await kot.content();
  ok(/Hot/.test(kt) && /Cheese/.test(kt) && /no onions/.test(kt) && /no salt/.test(kt) && /2×/.test(kt), 'KOT shows qty, options, notes');
  ok(!/630|1,?260|Total/i.test(kt.replace(/<style[\s\S]*?<\/style>/, '')), 'KOT has no prices');
  await kot.screenshot({ path: sh('53-kot') }).catch(() => {}); await kot.close().catch(() => {});

  // ---- 4. dine-in, move table, split, equal pay
  await p.goto(B + '/pos'); await p.waitForSelector('[data-testid^="tile-"]');
  const fv = (await j('GET', `/catalog/products/${fries.id}/`)).variants[0].id, pv = (await j('GET', `/catalog/products/${pizza.id}/`)).variants[0].id;
  await p.getByTestId(`tile-${fv}`).click(); await p.getByRole('button', { name: 'Add one more Fries' }).click();
  await p.getByTestId(`tile-${pv}`).click();
  await p.getByRole('button', { name: 'Dine-in', exact: true }).click(); await p.getByTestId('choose-table').click(); await p.waitForSelector('text=Choose a table');
  await p.locator('[role=dialog] svg[role=img]').first().click();
  await p.getByRole('button', { name: /Send to kitchen/ }).click(); await p.waitForSelector('[data-testid="done-number"]');
  const dnum = await p.getByTestId('done-number').innerText();
  let od = L(await j('GET', '/orders/')).find(x => x.order_number === dnum); const t1 = od.table;
  step('dine-in items: ' + od.items.map(i => i.quantity + '×' + i.product_name));
  await p.goto(B + '/orders'); await p.waitForSelector(`text=${dnum}`);
  const card = () => p.locator('div.p-5').filter({ hasText: dnum }).first();
  await card().getByTestId('move-table').click(); await p.waitForSelector('text=Choose a table');
  await p.screenshot({ path: sh('54-move-table') });
  const svgs = p.locator('[role=dialog] svg[role=img]'); const n = await svgs.count();
  for (let i = 0; i < n; i++) { await svgs.nth(i).click({ trial: true }).catch(() => {}); }
  await svgs.nth(1).click(); await p.waitForTimeout(1200);
  od = L(await j('GET', '/orders/')).find(x => x.order_number === dnum); ok(od.table !== t1, 'order moved to the other table');
  const tbls = L(await j('GET', '/orders/tables/')); ok(tbls.find(x => x.id === t1).status === 'AVAILABLE', 'old table freed');
  // split
  await card().getByTestId('split-bill').click(); await p.waitForSelector('[data-testid=split-confirm]');
  const first = od.items[0]; await p.locator('[role=dialog]').getByRole('button', { name: 'More', exact: true }).first().click();
  await p.screenshot({ path: sh('55-split-bill') });
  await p.getByTestId('split-confirm').click(); await p.waitForSelector('text=separate bill, text=New bill', { timeout: 5000 }).catch(() => {}); await p.waitForTimeout(1200);
  const all = L(await j('GET', '/orders/')).filter(x => x.table === od.table && x.status !== 'CANCELLED'); ok(all.length === 2, 'split created a second bill on the same table');
  const sum = all.reduce((a, x) => a + Number(x.total_amount), 0); const before = Number(od.total_amount); ok(Math.abs(sum - before) < 0.05, `totals add up (${sum} vs ${before})`);
  // equal pay on original
  await p.reload(); await p.waitForSelector(`text=${dnum}`);
  await card().getByRole('button', { name: /Pay|Take payment/ }).first().click(); await p.waitForSelector('[data-testid=guests-2]');
  await p.getByTestId('guests-2').click(); const due = Number(L(await j('GET', '/orders/')).find(x => x.order_number === dnum).total_amount);
  const amt1 = Number(await p.getByLabel('Amount to pay now').inputValue()); ok(Math.abs(amt1 - Math.round(due / 2 * 100) / 100) < 0.01, `guest 1 share = ${amt1} of ${due}`);
  await p.screenshot({ path: sh('56-equal-split') });
  await p.getByRole('button', { name: /^Receive/ }).click(); await p.waitForTimeout(1200);
  const amt2 = Number(await p.getByLabel('Amount to pay now').inputValue()); ok(Math.abs(amt1 + amt2 - due) < 0.011, `guest 2 pays the remainder ${amt2}`);
  await p.getByRole('button', { name: /^Receive/ }).click(); await p.waitForSelector('text=Paid in full');
  ok(true, 'order paid in two equal shares');

  // ---- 5. offline order with options syncs
  await p.goto(B + '/pos'); await p.waitForSelector('[data-testid^="tile-"]'); await p.waitForTimeout(1200);
  await ctx.setOffline(true);
  await p.getByTestId(`tile-${zv}`).click(); await p.waitForSelector('[data-testid=opt-add]');
  await p.getByTestId(`opt-${g1.options.find(o => o.name === 'Mild').id}`).click(); await p.getByTestId(`opt-${g2.options.find(o => o.name === 'Egg').id}`).click(); await p.getByTestId('opt-add').click();
  await p.getByRole('button', { name: /Save order/ }).click(); await p.waitForSelector('[data-testid="done-number"]');
  const off = await p.getByTestId('done-number').innerText(); ok(off.startsWith('OFF-'), 'offline order saved ' + off);
  const [kot2] = await Promise.all([ctx.waitForEvent('page'), p.getByTestId('print-kot').click()]); await kot2.waitForLoadState(); ok(/Egg/.test(await kot2.content()), 'offline KOT prints with options'); await kot2.close();
  await ctx.setOffline(false);
  let synced = null; for (let i = 0; i < 40 && !synced; i++) { await p.waitForTimeout(1000); synced = L(await j('GET', '/orders/')).find(x => x.items.some(it => it.modifiers?.some(m => m.name === 'Egg') && it.modifiers.some(m => m.name === 'Mild'))); }
  step('synced: ' + JSON.stringify(synced && synced.items.map(i=>[i.unit_price,i.modifiers.map(m=>m.name)])));
  ok(!!synced && Number(synced.items[0].unit_price) === 580, 'offline order synced with options, price 580');

  await p.goto(B + '/orders'); await p.waitForTimeout(1500); await p.screenshot({ path: sh('57-orders-options'), fullPage: true });
  ok(errs.length === 0, 'no page errors ' + errs.join('|'));
  await br.close(); console.log('STEP5 E2E PASSED');
})().catch(e => { console.error(e); process.exit(1); });
