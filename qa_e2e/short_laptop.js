const { chromium } = require('playwright'); const B='http://localhost:3101';
const VP=[[1093,560],[1280,600],[1366,650],[1366,768],[1024,600],[900,560],[820,500],[1920,1080],[390,844]];
(async()=>{const b=await chromium.launch();let bad=0;
for(const [w,h] of VP){const c=await b.newContext({viewport:{width:w,height:h}});const p=await c.newPage();
await p.goto(B+'/login');await p.waitForSelector('text=Welcome back');await p.getByLabel('Username').fill('karachigrill');await p.getByLabel('Password',{exact:true}).fill('Demo@12345');await p.click('button[type=submit]');await p.waitForURL(/dashboard/);
await p.goto(B+'/pos');await p.waitForSelector('[data-testid^="tile-"]');await p.waitForTimeout(800);
const r=await p.evaluate(()=>{const t=[...document.querySelectorAll('[data-testid^="tile-"]')];const tops=t.map(e=>Math.round(e.getBoundingClientRect().top));const cols=tops.filter(x=>x===tops[0]).length;
const aside=document.querySelector('aside.hidden.md\\:block > div, aside:not(.sticky) > div');return{cols,hov:document.documentElement.scrollWidth-document.documentElement.clientWidth}});
let cart='n/a';
if(w>=768){const tiles=p.locator('[data-testid^="tile-"]');for(const i of [0,1,2,3,4,5])await tiles.nth(i).click();await p.waitForTimeout(300);
 const btn=p.getByRole('button',{name:/Send to kitchen|Save order/});const bb=await btn.boundingBox();const dl=await p.getByRole('button',{name:'Delivery'}).boundingBox();const ct=await p.evaluate(()=>{const c=document.querySelector('aside.md\\:block > div');const r=c.getBoundingClientRect();return{top:r.top,bottom:r.bottom}});
 const sendOk=bb&&bb.y>=0&&bb.y+bb.height<=h+1; const tabOk=dl&&dl.y>=ct.top&&dl.y+dl.height<=ct.bottom;
 await p.mouse.move(w-150,h/2);await p.mouse.wheel(0,400);await p.waitForTimeout(300);const dl2=await p.getByRole('button',{name:'Delivery'}).boundingBox();
 cart=(sendOk?'send visible w/o scrolling':'send HIDDEN '+JSON.stringify(bb))+' | tabs '+(tabOk?'fully visible':'HIDDEN')+' | cart scroll '+(dl2&&dl2.y<dl.y?'works':'static(fits)')}
else{await p.locator('[data-testid^="tile-"]').first().click();await p.getByRole('button',{name:/View order/}).click();await p.waitForTimeout(400);const btn=p.getByRole('button',{name:/Send to kitchen/});await btn.scrollIntoViewIfNeeded();const bb=await btn.boundingBox();cart=bb&&bb.y+bb.height<=h+1?'modal send visible':'modal send HIDDEN'}
const bad1=r.hov>0||cart.includes('HIDDEN');if(bad1)bad++;console.log((bad1?'BAD ':'ok  ')+w+'x'+h,'cols',r.cols,'hscroll',r.hov,cart);
if(w===1093)await p.screenshot({path:'short_1093.png'});await c.close()}
console.log(bad?'FAILED '+bad:'ALL OK');await b.close()})()
