const fs = require('fs'); const { randomUUID } = require('crypto');
const A = 'http://localhost:8000/api/v1';
(async () => {
  const lg = await (await fetch(A + '/auth/token/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: 'zinger', password: 'Zinger-Pass-2026' }) })).json();
  const j = async (m, u, b) => { const r = await fetch(A + u, { method: m, headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + lg.access }, body: b ? JSON.stringify(b) : undefined }); const x = await r.text(); if (!r.ok) throw new Error(m + u + ' ' + r.status + x.slice(0, 300)); return x ? JSON.parse(x) : null; };
  const L = (x) => x.results ?? x;
  const cats = {}; for (const n of ['Burgers', 'Pizza', 'Desi', 'Drinks & Sides']) cats[n] = await j('POST', '/catalog/categories/', { name: n, slug: n.toLowerCase().replace(/[^a-z]+/g, '-') });
  const menu = [['Burgers', 'Zinger Burger', 550], ['Burgers', 'Beef Burger', 650], ['Pizza', 'Margherita Pizza', 1100], ['Pizza', 'BBQ Pizza', 1400], ['Desi', 'Chicken Karahi', 1900], ['Desi', 'Seekh Kabab', 850], ['Desi', 'Garlic Naan', 60], ['Drinks & Sides', 'Fries', 300], ['Drinks & Sides', 'Mint Margarita', 280], ['Drinks & Sides', 'Doodh Patti', 180], ['Burgers', 'Chicken Wings', 700], ['Drinks & Sides', 'Brownie', 350]];
  const pv = {};
  for (const [c, n, price] of menu) {
    const p = await j('POST', '/catalog/products/', { category: cats[c].id, name: n, slug: n.toLowerCase().replace(/ /g, '-'), sku: n.slice(0, 3).toUpperCase() + Math.floor(100 + Math.random() * 899), variants: [{ name: 'Regular', base_price: String(price) }] });
    const fd = new FormData(); fd.append('image', new Blob([fs.readFileSync(__dirname + '/img/' + n.toLowerCase().replace(/ /g, '-') + '.jpg')], { type: 'image/jpeg' }), 'x.jpg');
    const r = await fetch(A + `/catalog/products/${p.id}/`, { method: 'PATCH', headers: { Authorization: 'Bearer ' + lg.access }, body: fd }); if (!r.ok) console.log('img fail', n, r.status);
    pv[n] = (await j('GET', `/catalog/products/${p.id}/`)).variants[0].id;
  }
  const g = await j('POST', '/orders/floors/', { location: 1, name: 'Ground Floor', level: 0 }); const rf = await j('POST', '/orders/floors/', { location: 1, name: 'Rooftop', level: 1 });
  const tb = []; const shapes = ['SQUARE', 'ROUND', 'SQUARE', 'ROUND', 'SQUARE', 'ROUND'];
  for (let i = 0; i < 6; i++) tb.push(await j('POST', '/orders/tables/', { floor: g.id, location: 1, table_number: 'T-' + (i + 1), capacity: [4, 2, 6, 2, 4, 4][i], shape: shapes[i] }));
  for (let i = 0; i < 3; i++) tb.push(await j('POST', '/orders/tables/', { floor: rf.id, location: 1, table_number: 'T-' + (i + 7), capacity: 4, shape: 'ROUND' }));
  await j('POST', '/cash/shifts/open/', { location: 1, opening_cash: '5000' });
  await j('PATCH', '/loyalty/settings/', { enabled: true, spend_per_point: '100', point_value: '1', min_redeem: 100 });
  const names = Object.keys(pv); const custs = [['Ali Khan', '03001112221'], ['Sara Ahmed', '03001112222'], ['Bilal Raza', '03001112223'], ['Hina Malik', '03001112224'], ['Usman Tariq', '03001112225']];
  const types = ['TAKEAWAY', 'DINE_IN', 'DELIVERY'];
  const mk = async (i, pay) => {
    const c = custs[i % custs.length]; const type = types[i % 3];
    const items = [0, 1, 2].slice(0, 1 + (i % 3)).map((k) => ({ product_variant: pv[names[(i * 3 + k) % names.length]], quantity: 1 + ((i + k) % 3) }));
    const body = { client_uuid: randomUUID(), location: 1, order_type: type, customer_name: c[0], customer_phone: c[1], customer_email: i % 2 ? `${c[0].split(' ')[0].toLowerCase()}@example.com` : '', items };
    if (type === 'DINE_IN') body.table = tb[i % 6].id; if (type === 'DELIVERY') body.delivery_address = 'House 12, Street 4, Gulberg, Lahore';
    const o = (await j('POST', '/orders/sync/', body)).order;
    if (pay) { const t = Number((await j('GET', `/orders/${o.id}/`)).total_amount); await j('POST', `/cash/orders/${o.id}/payments/`, { method: ['CASH', 'CARD', 'WALLET'][i % 3], amount: String(t) }).catch((e) => console.log('pay', e.message.slice(0, 120))); }
    return o;
  };
  for (let i = 0; i < 14; i++) await mk(i, i < 11);
  const all = L(await j('GET', '/orders/?page_size=50'));
  const bump = async (o, sts) => { for (const st of sts) await j('POST', `/orders/${o.id}/status/`, { status: st }).catch((e) => console.log('st', st, e.message.slice(0, 100))); };
  const open = all.filter((o) => o.status === 'CONFIRMED' || o.status === 'PENDING');
  for (const [k, o] of open.entries()) { if (k % 4 === 0) await bump(o, ['PREPARING']); else if (k % 4 === 1) await bump(o, ['PREPARING', 'READY']); }
  console.log('orders ok');
  const ing = {}; for (const [n, u] of [['Chicken', 'G'], ['Beef', 'G'], ['Burger Buns', 'PCS'], ['Cheese', 'G'], ['Cooking Oil', 'ML'], ['Flour', 'G']]) ing[n] = await j('POST', '/inventory/ingredients/', { name: n, base_unit: u });
  const sup = await j('POST', '/operations/suppliers/', { name: 'Fresh Poultry Traders', phone: '03211234567' });
  await j('POST', '/operations/purchases/', { location: 1, supplier: sup.id, invoice_no: 'INV-1042', paid: '30000', lines: [{ ingredient: ing.Chicken.id, quantity: 20000, unit: 'G', unit_cost: 0.9 }, { ingredient: ing.Beef.id, quantity: 8000, unit: 'G', unit_cost: 1.4 }, { ingredient: ing['Burger Buns'].id, quantity: 300, unit: 'PCS', unit_cost: 25 }, { ingredient: ing.Cheese.id, quantity: 3000, unit: 'G', unit_cost: 1.8 }, { ingredient: ing['Cooking Oil'].id, quantity: 15000, unit: 'ML', unit_cost: 0.5 }, { ingredient: ing.Flour.id, quantity: 25000, unit: 'G', unit_cost: 0.12 }] }).catch((e) => console.log('purchase', e.message));
  for (const [cat, d, a] of [['Gas', 'Gas cylinder refill', 9500], ['Electricity', 'Monthly bill', 42000], ['Salaries', 'Advance', 15000], ['Cleaning', 'Supplies', 3200]]) await j('POST', '/operations/expenses/', { location: 1, category: cat, description: d, amount: String(a) }).catch((e) => console.log('exp', e.message));
  const t0 = new Date(); t0.setHours(20, 0, 0, 0); if (t0 < new Date()) t0.setDate(t0.getDate() + 1);
  for (const [i, n] of ['Imran Sheikh', 'Zara Noor', 'Farhan Ali'].entries()) { const s = new Date(t0.getTime() + i * 90 * 60000); await j('POST', '/operations/reservations/', { location: 1, table: tb[[0, 2, 4][i]].id, guest_name: n, phone: '0322555000' + i, party_size: 2 + i, starts_at: s.toISOString() }).catch((e) => console.log('res', e.message.slice(0, 160))); }
  const mkE = async (name, role, pt, amt) => { const e = await j('POST', '/staff/employees/', { location: 1, name, role, phone: '0300' + Math.floor(1e6 + Math.random() * 8e6), joining_date: '2026-10-01' }); await j('PUT', `/payroll/employees/${e.id}/profile/`, { pay_type: pt, base_amount: amt }); };
  await mkE('Bilal Ahmed', 'CASHIER', 'DAILY', '1500'); await mkE('Sara Khan', 'WAITER', 'DAILY', '1200'); await mkE('Usman Ali', 'CHEF', 'MONTHLY', '60000'); await mkE('Kashif Mehmood', 'MANAGER', 'MONTHLY', '85000');
  const d = new Date(); await j('POST', '/payroll/runs/', { location: 1, month: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}` }).catch((e) => console.log('run', e.message.slice(0, 120)));
  console.log('seed done');
})().catch(e => { console.log('ERR', e.message); process.exit(1); });
