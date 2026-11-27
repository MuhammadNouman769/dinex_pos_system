const { chromium } = require('playwright'); const B='http://localhost:3101';
(async()=>{const b=await chromium.launch();const c=await b.newContext();const a=await c.newPage();
await a.goto(B+'/login');await a.waitForSelector('text=Welcome back');await a.getByLabel('Username').fill('karachigrill');await a.getByLabel('Password',{exact:true}).fill('Demo@12345');await a.click('button[type=submit]');await a.waitForURL(/dashboard/);
const t=[];for(let i=0;i<3;i++){const p=await c.newPage();await p.goto(B+'/dashboard');t.push(p)}
let fails=0;
for(let round=1;round<=4;round++){
  // simulate access token expiry in the shared browser storage, then make every tab call the API at the same moment
  await a.evaluate(()=>localStorage.setItem('dinex_access','expired.invalid.token'));
  await Promise.all([a,...t].map(p=>p.reload().catch(()=>{})));
  await Promise.all([a,...t].map(p=>p.waitForTimeout(3500)));
  const urls=[a,...t].map(p=>new URL(p.url()).pathname);const ok=urls.every(u=>!/login/.test(u));
  console.log('round',round,ok?'all tabs still signed in':'LOGGED OUT '+urls.join(','));if(!ok)fails++}
console.log(fails?'FAILED':'ALL OK');await b.close()})()
