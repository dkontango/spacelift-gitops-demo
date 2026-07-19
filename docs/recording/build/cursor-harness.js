// Yellow-halo cursor overlay + PII redaction harness.
// Injected into each live page (Spacelift / AWS console / GitHub) before capture.
// Exposes window.__wiz with: cursor(), moveTo(x,y,steps), pulse(), redact().
//
// Playwright drives it via page.evaluate; frames are captured by the caller
// between motion steps. The cursor is a DOM element so it renders in screenshots
// (a real OS cursor does not).

(function () {
  if (window.__wiz) return; // idempotent

  // --- yellow-halo cursor ---
  const c = document.createElement('div');
  c.id = '__wiz_cursor';
  Object.assign(c.style, {
    position: 'fixed', left: '0px', top: '0px', width: '22px', height: '22px',
    borderRadius: '50%', pointerEvents: 'none', zIndex: '2147483647',
    transform: 'translate(-50%,-50%)',
    background: 'radial-gradient(circle at 50% 45%, #fff6b0 0%, #ffe14d 35%, rgba(255,208,0,0.55) 60%, rgba(255,200,0,0) 75%)',
    boxShadow: '0 0 14px 6px rgba(255,214,0,0.85), 0 0 34px 16px rgba(255,214,0,0.35)',
    transition: 'none',
  });
  // a small arrow to read as a pointer
  const tip = document.createElement('div');
  Object.assign(tip.style, {
    position: 'absolute', left: '50%', top: '50%', width: '0', height: '0',
    borderLeft: '7px solid transparent', borderRight: '7px solid transparent',
    borderTop: '12px solid rgba(40,30,0,0.9)',
    transform: 'translate(-50%,-30%) rotate(-30deg)',
  });
  c.appendChild(tip);
  document.documentElement.appendChild(c);

  let cx = window.innerWidth * 0.5, cy = window.innerHeight * 0.4;
  function place(x, y) { cx = x; cy = y; c.style.left = x + 'px'; c.style.top = y + 'px'; }
  place(cx, cy);

  window.__wiz = {
    at() { return { x: cx, y: cy }; },
    place,
    // move directly (caller captures frames between calls for smoothness)
    step(x, y) { place(x, y); },
    // click pulse: expanding ring that fades
    pulse() {
      const r = document.createElement('div');
      Object.assign(r.style, {
        position: 'fixed', left: cx + 'px', top: cy + 'px', width: '10px', height: '10px',
        borderRadius: '50%', pointerEvents: 'none', zIndex: '2147483646',
        transform: 'translate(-50%,-50%)', border: '3px solid rgba(255,214,0,0.9)',
        boxShadow: '0 0 12px 4px rgba(255,214,0,0.6)',
        transition: 'width .35s ease-out, height .35s ease-out, opacity .35s ease-out, border-width .35s',
        opacity: '1',
      });
      document.documentElement.appendChild(r);
      requestAnimationFrame(() => {
        r.style.width = '54px'; r.style.height = '54px'; r.style.opacity = '0'; r.style.borderWidth = '1px';
      });
      setTimeout(() => r.remove(), 420);
    },
    // locate a target: css selector OR text; returns viewport-center coords
    find(sel, text) {
      let el = null;
      if (sel) { try { el = document.querySelector(sel); } catch (e) {} }
      if (!el && text) {
        const t = text.toLowerCase();
        const all = document.querySelectorAll('button,a,span,div,td,th,h1,h2,h3,label,code,li');
        for (const n of all) {
          const s = (n.textContent || '').trim().toLowerCase();
          if (s && s.length < 120 && s.includes(t)) {
            const rr = n.getBoundingClientRect();
            if (rr.width && rr.height && rr.top >= 0 && rr.top < window.innerHeight) { el = n; break; }
          }
        }
      }
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + Math.min(r.height / 2, 18)) };
    },
    // redact ARNs, 12-digit AWS account ids, emails -> black boxes
    redact() {
      const rx = [
        /arn:aws[a-z-]*:[^\s"'<>]+/gi,
        /\b\d{12}\b/g,
        /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g,
        /AKIA[0-9A-Z]{16}/g,
      ];
      const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      const hits = [];
      let node;
      while ((node = walk.nextNode())) {
        const v = node.nodeValue;
        if (!v || !v.trim()) continue;
        if (rx.some((r) => (r.lastIndex = 0, r.test(v)))) hits.push(node);
      }
      let n = 0;
      for (const t of hits) {
        const parent = t.parentElement;
        if (!parent || parent.closest('#__wiz_cursor')) continue;
        let html = t.nodeValue;
        for (const r of rx) { r.lastIndex = 0; html = html.replace(r, (m) => '█'.repeat(Math.min(m.length, 14))); }
        // replace the text node with a span carrying black-box styling on the runs
        const span = document.createElement('span');
        span.textContent = html;
        span.style.cssText = 'background:#111;color:#111;border-radius:3px;';
        parent.replaceChild(span, t);
        n++;
      }
      return n;
    },
  };
})();
