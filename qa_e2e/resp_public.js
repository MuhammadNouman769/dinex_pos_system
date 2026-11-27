const { chromium } = require('playwright');
const B='http://localhost:3101'; const VP=[[360,740],[390,844],[430,932],[768,1024],[1024,768],[1280,800],[1440,900],[1920,1080]];
(async()=>{const b=await chromium.launch();let bad=0;
for(const pg of ['/','/start','/terms','/login']){for(const [w,h] of VP){const c=await b.newContext({viewport:{width:w,height:h}});const p=await c.newPage();const errs=[];p.on('pageerror',e=>errs.push(e.message));
await p.goto(B+pg);await p.waitForTimeout(500);const o=await p.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
if(o>0||errs.length){bad++;console.log('BAD',pg,w,o,errs)}
if(pg==='/'&&[390,1440].includes(w)){await p.screenshot({path:`shots/landing_${w}.png`,fullPage:true})}
await c.close()}}
console.log(bad?'FAILED '+bad:'ALL OK (4 pages x 8 viewports)');await b.close()})()
