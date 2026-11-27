const { chromium } = require('playwright'); const S = __dirname, B = 'http://localhost:3101';
const VPS = [[360, 740, 'phone-s'], [390, 844, 'phone'], [768, 1024, 'tablet'], [1024, 768, 'tablet-land'], [1280, 800, 'laptop'], [1366, 768, 'laptop-hd'], [1440, 900, 'desktop'], [1920, 1080, 'full-hd']];
const PAGES = ['dashboard', 'pos', 'orders', 'kitchen', 'tables', 'reservations', 'customers', 'cash', 'inventory', 'purchases', 'expenses', 'reports', 'day-report', 'payroll', 'staff', 'setup', 'billing'];
(async () => {
  const br = await chromium.launch(); let fails = 0; const rows = [];
  for (const [w, h, name] of VPS) {
    const c = await br.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1, isMobile: w < 800, hasTouch: w < 800 }); const p = await c.newPage(); const errs = []; p.on('pageerror', e => errs.push(String(e)));
    await p.goto(B + '/login'); await p.getByLabel(/Username/i).fill('zinger'); await p.getByLabel('Password', { exact: true }).fill('Zinger-Pass-2026'); await p.getByRole('button', { name: /sign in|log in/i }).click(); await p.waitForURL(/setup|dashboard|pos/);
    for (const pg of PAGES) {
      await p.goto(B + '/' + pg); await p.waitForTimeout(900);
      const r = await p.evaluate(() => { const de = document.documentElement; const over = de.scrollWidth - de.clientWidth; const wide = [...document.querySelectorAll('body *')].filter(e => { const b = e.getBoundingClientRect(); return b.width > 0 && b.right > de.clientWidth + 2 && !e.closest('[class*="overflow-x"],[class*="overflow-auto"],table,pre'); }).slice(0, 2).map(e => e.tagName + '.' + String(e.className).slice(0, 40)); return { over, wide }; });
      if (r.over > 1) { fails++; console.log(`OVERFLOW ${name} ${w}px /${pg}: +${r.over}px`, r.wide.join(' | ')); }
    }
    await p.goto(B + '/pos'); await p.waitForSelector('[data-testid^="tile-"]'); await p.waitForTimeout(600);
    const g = await p.evaluate(() => { const t = [...document.querySelectorAll('[data-testid^="tile-"]')].map(e => e.getBoundingClientRect()); const top = t[0].top; const first = t.filter(b => Math.abs(b.top - top) < 4); const overlap = t.some((a, i) => t.some((b, j) => i < j && a.left < b.right - 2 && b.left < a.right - 2 && a.top < b.bottom - 2 && b.top < a.bottom - 2)); const cart = !!document.querySelector('aside') && getComputedStyle(document.querySelector('aside')).display !== 'none'; return { perRow: first.length, cardW: Math.round(first[0].width), overlap, cart }; });
    rows.push(`${name.padEnd(12)} ${String(w).padStart(4)}px  cards per row: ${g.perRow}  card width: ${g.cardW}px  cart panel: ${g.cart ? 'side' : 'sheet'}  overlap: ${g.overlap}`);
    if (g.overlap) fails++; if (errs.length) { fails++; console.log('page errors', name, errs.slice(0, 2)); }
    await p.screenshot({ path: `${S}/shots/rs-pos-${name}.png` }); await c.close();
  }
  console.log(rows.join('\n')); console.log(fails ? `FAILS: ${fails}` : 'RESPONSIVE OK'); await br.close(); process.exit(fails ? 1 : 0);
})();
