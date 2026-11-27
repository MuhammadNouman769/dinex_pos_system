const { chromium } = require('playwright');
const B = 'http://localhost:3101', OUT = '/home/claude/src_zip/dinex-web/public/images/';
(async () => {
  const b = await chromium.launch(); const c = await b.newContext({ viewport: { width: 1200, height: 750 } }); const p = await c.newPage();
  await p.goto(B + '/login'); await p.waitForSelector('text=Welcome back');
  await p.getByLabel('Username').fill('karachigrill'); await p.getByLabel('Password', { exact: true }).fill('Demo@12345'); await p.click('button[type=submit]');
  await p.waitForURL(/dashboard|setup/, { timeout: 20000 });
  const shot = async (name) => { await p.evaluate(() => { window.scrollTo(0, 0); document.querySelectorAll('main, [class*=overflow-y]').forEach(e => e.scrollTop = 0); }); await p.waitForTimeout(1500); await p.screenshot({ path: OUT + name + '-screen.jpg', type: 'jpeg', quality: 82 }); console.log('saved', name); };
  await p.goto(B + '/dashboard'); await shot('dashboard');
  await p.goto(B + '/pos'); await p.waitForTimeout(2500);
  for (const n of ['Chicken Biryani', 'Chapli Kabab', 'Beef Nihari']) await p.getByText(n, { exact: true }).first().click();
  await p.getByText('Chicken Biryani', { exact: true }).first().click();
  await p.getByPlaceholder(/phone/i).first().fill('03019636619'); await p.waitForTimeout(1500);
  await shot('pos');
  await p.goto(B + '/kitchen'); await shot('kitchen');
  await p.goto(B + '/tables'); await shot('tables');
  await p.goto(B + '/payroll'); await shot('payroll');
  await b.close();
})();
