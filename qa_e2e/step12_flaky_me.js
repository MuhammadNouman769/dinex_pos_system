const { chromium } = require('playwright'); const B='http://localhost:3000';
(async()=>{const b=await chromium.launch();const c=await b.newContext();const p=await c.newPage();
await p.goto(B+'/login');await p.waitForSelector('text=Welcome back',{timeout:60000});await p.getByLabel('Username').fill('karachigrill');await p.getByLabel('Password',{exact:true}).fill('Demo@12345');await p.click('button[type=submit]');await p.waitForURL(/dashboard/,{timeout:30000});console.log('login ok');
// server hiccup: /auth/me fails (500, then 429, then network error) for the next reloads, then recovers
let n=0;await p.route('**/auth/me/',r=>{n++;if(n===1)return r.fulfill({status:500,body:'{"detail":"database is locked"}'});if(n===2)return r.fulfill({status:429,body:'{"detail":"throttled"}'});if(n===3)return r.abort();return r.continue()});
await p.reload();await p.waitForTimeout(9000);console.log('after 3 failing /me calls ->',new URL(p.url()).pathname,'(calls',n+')');
console.log(/login/.test(p.url())?'FAIL: sent to login':'PASS: stayed signed in');
// real 401 must still log out
await p.unroute('**/auth/me/');await p.evaluate(()=>{localStorage.setItem('dinex_access','x.y.z');localStorage.setItem('dinex_refresh','x.y.z')});await p.reload();await p.waitForTimeout(4000);console.log(/login/.test(p.url())?'PASS: invalid token -> login':'FAIL: stayed with invalid token');
await b.close()})()
