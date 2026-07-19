// Master driver: captures the remaining live steps (Spacelift + GitHub) in one
// run — navigate, settle, close the Foundations panel, redact PII, run a
// multi-point yellow-cursor tour, write frames. One invocation = one tool echo.

async (page) => {
  const OUT = '/home/leonardo/git/spacelift-gitops-demo/docs/recording/frames17';

  const HARNESS = `(${function () {
    if (window.__wiz) { window.__wiz.reset && window.__wiz.reset(); return; }
    const c = document.createElement('div'); c.id = '__wiz_cursor';
    Object.assign(c.style, { position:'fixed', left:'0px', top:'0px', width:'22px', height:'22px',
      borderRadius:'50%', pointerEvents:'none', zIndex:'2147483647', transform:'translate(-50%,-50%)',
      background:'radial-gradient(circle at 50% 45%, #fff6b0 0%, #ffe14d 35%, rgba(255,208,0,0.55) 60%, rgba(255,200,0,0) 75%)',
      boxShadow:'0 0 14px 6px rgba(255,214,0,0.85), 0 0 34px 16px rgba(255,214,0,0.35)', transition:'none' });
    const tip = document.createElement('div');
    Object.assign(tip.style, { position:'absolute', left:'50%', top:'50%', width:'0', height:'0',
      borderLeft:'7px solid transparent', borderRight:'7px solid transparent',
      borderTop:'12px solid rgba(40,30,0,0.9)', transform:'translate(-50%,-30%) rotate(-30deg)' });
    c.appendChild(tip); document.documentElement.appendChild(c);
    let cx = window.innerWidth*0.5, cy = window.innerHeight*0.3;
    function place(x,y){ cx=x; cy=y; c.style.left=x+'px'; c.style.top=y+'px'; }
    place(cx,cy);
    window.__wiz = {
      reset(){ if(!document.getElementById('__wiz_cursor')) document.documentElement.appendChild(c); place(window.innerWidth*0.5, window.innerHeight*0.3); },
      at(){ return {x:cx,y:cy}; }, place, step(x,y){ place(x,y); },
      pulse(){ const r=document.createElement('div');
        Object.assign(r.style,{ position:'fixed', left:cx+'px', top:cy+'px', width:'10px', height:'10px',
          borderRadius:'50%', pointerEvents:'none', zIndex:'2147483646', transform:'translate(-50%,-50%)',
          border:'3px solid rgba(255,214,0,0.9)', boxShadow:'0 0 12px 4px rgba(255,214,0,0.6)',
          transition:'width .35s ease-out, height .35s ease-out, opacity .35s ease-out, border-width .35s', opacity:'1' });
        document.documentElement.appendChild(r);
        requestAnimationFrame(()=>{ r.style.width='54px'; r.style.height='54px'; r.style.opacity='0'; r.style.borderWidth='1px'; });
        setTimeout(()=>r.remove(),420); },
      find(sel,text){ let el=null;
        if(sel){ try{ el=document.querySelector(sel); }catch(e){} }
        if(!el && text){ const t=text.toLowerCase();
          const all=document.querySelectorAll('button,a,span,div,td,th,h1,h2,h3,label,code,li,input');
          for(const n of all){ const s=(n.textContent||'').trim().toLowerCase();
            if(s && s.length<200 && s.includes(t)){ const rr=n.getBoundingClientRect();
              if(rr.width && rr.height && rr.top>=40 && rr.top<window.innerHeight-30){ el=n; break; } } } }
        if(!el) return null; const r=el.getBoundingClientRect();
        return { x:Math.round(r.left+r.width/2), y:Math.round(r.top+Math.min(r.height/2,18)) }; },
      closePanels(){ const bs=document.querySelectorAll('button'); let n=0;
        for(const b of bs){ const l=(b.getAttribute('aria-label')||'')+' '+(b.title||'');
          if(/close assistant/i.test(l)){ b.click(); n++; } } return n; },
      redact(){
        const rx=[ new RegExp('arn:aws[a-z-]*:[^\\s"\'<>]+','gi'),
          new RegExp('\\b\\d{12}\\b','g'),
          new RegExp('[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}','g'),
          new RegExp('AKIA[0-9A-Z]{16}','g') ];
        const BX=String.fromCharCode(9608);
        const box=(m)=>BX.repeat(Math.min(m.length,14));
        const walk=document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); const hits=[]; let node;
        while((node=walk.nextNode())){ const v=node.nodeValue; if(!v||!v.trim()) continue;
          if(rx.some((r)=>(r.lastIndex=0, r.test(v)))) hits.push(node); }
        let n=0; for(const t of hits){ const parent=t.parentElement;
          if(!parent||parent.closest('#__wiz_cursor')) continue; let html=t.nodeValue;
          for(const r of rx){ r.lastIndex=0; html=html.replace(r,box); }
          const span=document.createElement('span'); span.textContent=html;
          span.style.cssText='background:#111;color:#111;border-radius:3px;';
          parent.replaceChild(span,t); n++; }
        document.querySelectorAll('[aria-label],[title]').forEach((el)=>{
          ['aria-label','title'].forEach((a)=>{ const v=el.getAttribute(a); if(!v) return;
            let nv=v; rx.forEach((r)=>{ r.lastIndex=0; nv=nv.replace(r,box); });
            if(nv!==v) el.setAttribute(a,nv); }); });
        return n; },
    };
  }.toString()})()`;

  const sleep = (ms) => page.waitForTimeout(ms);

  async function captureStep(step, url, targets, opts={}) {
    await page.goto(url, { waitUntil: 'domcontentloaded' });
    await sleep(opts.settle || 4500);
    // close the Foundations panel if present, then re-settle
    try { await page.evaluate(HARNESS); await page.evaluate(() => window.__wiz.closePanels()); } catch(e){}
    await sleep(800);
    await page.evaluate(HARNESS);
    const redacted = await page.evaluate(() => window.__wiz.redact());
    const pts = await page.evaluate((specs) => {
      const w = window.__wiz; const out = [];
      for (const s of specs) { const p = w.find(s.sel||null, s.text||null); if (p) out.push({label:s.label||s.text, ...p}); }
      return out;
    }, targets);
    let fi = 0;
    const shot = async () => { const n = String(fi++).padStart(3,'0'); await page.screenshot({ path: `${OUT}/step${step}-${n}.png` }); };
    const easeTo = async (tx,ty,frames=8) => {
      const start = await page.evaluate(() => window.__wiz.at());
      for (let i=1;i<=frames;i++){ const t=i/frames; const e=t<0.5?2*t*t:1-Math.pow(-2*t+2,2)/2;
        const x=Math.round(start.x+(tx-start.x)*e), y=Math.round(start.y+(ty-start.y)*e);
        await page.evaluate(([x,y])=>window.__wiz.step(x,y),[x,y]); await shot(); }
    };
    await shot(); await shot();
    for (const t of pts) { await easeTo(t.x,t.y,8); await page.evaluate(()=>window.__wiz.pulse()); await shot(); await shot(); await shot(); }
    await shot(); await shot();
    return { step, url: url.slice(0,60), frames: fi, redacted, found: pts.map(p=>p.label) };
  }

  const SL = 'https://dkontango.app.us.spacelift.io';
  const results = [];

  // Step 6 — AWS integrations list (account-level)
  results.push(await captureStep('06', `${SL}/integrations/aws`, [
    {label:'aws-integrations', text:'Integrations'}, {label:'orbit-role', text:'aws-orbit-labs-role'},
  ]));

  // Step 7 — the sandbox stack (tracked runs / details)
  results.push(await captureStep('07', `${SL}/stack/spacelift-gitops-demo-sandbox`, [
    {label:'stack-name', text:'spacelift-gitops-demo-sandbox'}, {label:'tracked-runs', text:'Tracked runs'},
  ]));

  // Step 11 — the policies list (Plan policy present)
  results.push(await captureStep('11', `${SL}/policies`, [
    {label:'policies', text:'Policies'}, {label:'plan-policy', text:'plan-block-public-s3'},
  ]));

  return results;
}
