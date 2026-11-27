const A='http://localhost:8000/api/v1';
(async()=>{
 const j=async(m,u,b,t)=>{const r=await fetch(A+u,{method:m,headers:{'Content-Type':'application/json',...(t?{Authorization:'Bearer '+t}:{})},body:b?JSON.stringify(b):undefined});const x=await r.text();let d;try{d=JSON.parse(x)}catch{d=x};if(!r.ok)throw new Error(m+u+' '+r.status+' '+x.slice(0,300));return d};
 const s=await j('POST','/public/signup/',{plan:'growth',restaurant_name:'Zinger House',owner_name:'Ali Raza',email:'ali@zinger.pk',phone:'03001234567',username:'zinger',password:'Zinger-Pass-2026',address:'Main Boulevard, Gulberg, Lahore',accept_terms:true});
 console.log(Object.keys(s), JSON.stringify(s).slice(0,400));
 const t=s.access||s.tokens?.access;
 const me=await j('GET','/auth/me/',null,t).catch(e=>e.message); console.log(JSON.stringify(me).slice(0,600));
})().catch(e=>console.log('ERR',e.message));
