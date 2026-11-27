// Step 10: SEO / Google indexing checks
const { chromium } = require('playwright');
const B = process.env.WEB || 'http://localhost:3101', API = process.env.API || 'http://localhost:8000/api/v1';
let fail = 0; const ok = (c, m) => { console.log((c ? 'PASS ' : 'FAIL ') + m); if (!c) fail++; };
(async () => {
  const get = async (u) => { const r = await fetch(B + u); return { r, t: await r.text() }; };
  let { r, t } = await get('/robots.txt');
  ok(r.ok && /Sitemap: .*\/sitemap\.xml/.test(t) && /Disallow: \/dashboard/.test(t) && /Allow: \//.test(t), 'robots.txt has sitemap + private disallows');
  ok(!/Disallow: \/login/.test(t), 'robots.txt lets Google see noindex on /login');
  ({ r, t } = await get('/sitemap.xml'));
  ok(r.ok && /<loc>[^<]+\/<\/loc>/.test(t) && /\/terms/.test(t) && !/dashboard|login/.test(t), 'sitemap.xml lists / and /terms only');
  ({ r, t } = await get('/'));
  ok((t.match(/<h1/g) || []).length === 1, 'home has exactly one H1');
  ok(/<title>[^<]{10,}/.test(t), 'home has a title');
  ok(/name="description" content="[^"]{50,}/.test(t), 'home has meta description');
  ok(/rel="canonical"/.test(t), 'home has canonical');
  ok(/property="og:image"/.test(t) && /name="twitter:card"/.test(t), 'home has og:image + twitter card');
  const ld = [...t.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/g)].map(m => JSON.parse(m[1]));
  const types = ld.flatMap(x => x['@graph'] || [x]).map(x => x['@type']);
  ok(['Organization', 'WebSite', 'SoftwareApplication', 'FAQPage'].every(k => types.includes(k)), 'JSON-LD has Organization, WebSite, SoftwareApplication, FAQPage: ' + types);
  const prices = ld.flatMap(x => x['@graph'] || [x]).find(x => x['@type'] === 'SoftwareApplication').offers.map(o => o.price);
  ok(prices.join() === '2999,4999,6999', 'offers prices ' + prices);
  ok(!/<img(?![^>]*alt=)/.test(t), 'every img has alt');
  ok(/PKR 2,999/.test(t) && /PKR 6,999/.test(t), 'pricing shown in HTML (server rendered)');
  for (const u of ['/login', '/forgot-password', '/signup', '/start', '/plans']) {
    const x = await get(u); ok(/name="robots" content="noindex/.test(x.t) || /noindex/.test(x.r.headers.get('x-robots-tag') || ''), u + ' is noindex');
  }
  const d = await fetch(B + '/dashboard'); ok(/noindex/.test(d.headers.get('x-robots-tag') || ''), '/dashboard has X-Robots-Tag noindex');
  const og = await fetch(B + '/opengraph-image'); const buf = Buffer.from(await og.arrayBuffer());
  ok(og.headers.get('content-type') === 'image/png' && buf.length > 5000 && buf.readUInt32BE(16) === 1200 && buf.readUInt32BE(20) === 630, 'opengraph-image is 1200x630 PNG');
  for (const u of ['/icon.png', '/apple-icon.png', '/manifest.webmanifest', '/terms']) ok((await fetch(B + u)).ok, u + ' is served');
  const tm = await get('/terms'); ok(/<title>Terms of Use · DineX<\/title>/.test(tm.t) && !/noindex/.test(tm.t), '/terms title ok and indexable');
  // browser: signed-in user is redirected away from "/"
  const br = await chromium.launch(); const p = await (await br.newContext()).newPage();
  await p.goto(B + '/'); ok(await p.locator('h1').innerText().then(s => /offline/i.test(s)), 'anonymous user sees landing');
  await p.click('a[href="/start"] >> nth=0'); await p.waitForURL('**/start'); await p.waitForSelector('text=Terms of Use',{timeout:10000}).then(()=>ok(true,'CTA opens /start (terms)'),()=>ok(false,'CTA opens /start (terms)'));
  {
    const ctx2 = await br.newContext(); const q = await ctx2.newPage(); await q.goto(B + '/login'); await q.waitForSelector('text=Welcome back');
    await q.getByLabel('Username').fill('karachigrill'); await q.getByLabel('Password', { exact: true }).fill('Demo@12345');
    await q.click('button[type="submit"]'); await q.waitForURL(/dashboard|admin|setup/, { timeout: 15000 });
    await q.goto(B + '/'); await q.waitForURL(/dashboard|admin|setup/, { timeout: 10000 }); ok(true, 'signed-in user redirected from / to ' + new URL(q.url()).pathname);
  }
  await br.close(); console.log(fail ? `FAILED ${fail}` : 'ALL OK'); process.exit(fail ? 1 : 0);
})();
