#!/usr/bin/env python3
"""Build the static guide site from the docs/*.md sources. Dependency-free.

Renders a small, well-known subset of Markdown (headings, fenced code, tables,
blockquotes, lists, links, inline code, bold) into styled HTML pages wrapped in a
shared template with a nav sidebar. Output goes to site/ (index.html + pages).

Run: python3 site/build.py
"""
import html
import re
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")

# Public URL of the self-hosted Go contact-service (SMTP relay behind it). The
# contact form on index.html POSTs here. Override at build time:
#   CONTACT_ENDPOINT=https://spacelift-demo-contact.kontango.net/contact python3 site/build.py
CONTACT_ENDPOINT = os.environ.get(
    "CONTACT_ENDPOINT", "https://spacelift-demo-contact.kontango.net/contact"
)

# (nav label, output filename, source markdown or None for the hand-written index)
# "WIZARD" as the source means: build the swipeable step wizard from
# docs/illustrated-walkthrough.md instead of rendering it as a scroll page.
PAGES = [
    ("Overview", "index.html", None),
    ("Illustrated Walkthrough", "walkthrough.html", "WIZARD"),
    ("Onboarding — By Hand", "by-hand.html", "docs/onboarding-by-hand.md"),
    ("Onboarding — With AI", "with-ai.html", "docs/onboarding-with-ai.md"),
    ("AI Agent Context (AGENTS.md)", "agents.html", "AGENTS.md"),
    ("Troubleshooting: AWS creds", "troubleshooting.html", "docs/troubleshooting-aws-credentials.md"),
]


def md_to_html(md: str) -> str:
    """Minimal but correct-enough Markdown -> HTML for our docs."""
    lines = md.split("\n")
    out = []
    i = 0
    n = len(lines)

    def inline(t: str) -> str:
        t = html.escape(t, quote=False)
        # inline code first (protect its contents)
        codes = []
        def stash(m):
            codes.append(m.group(1))
            return f"\x00{len(codes)-1}\x00"
        t = re.sub(r"`([^`]+)`", stash, t)
        # images ![alt](src) — before links (same bracket syntax)
        t = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1" loading="lazy">', t)
        # links [text](url)
        t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
        # bold
        t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
        # restore code
        def unstash(m):
            return "<code>" + html.escape(codes[int(m.group(1))], quote=False) + "</code>"
        t = re.sub(r"\x00(\d+)\x00", unstash, t)
        return t

    while i < n:
        line = lines[i]

        # fenced code block
        if line.strip().startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1  # skip closing fence
            out.append("<pre><code>" + html.escape("\n".join(buf), quote=False) + "</code></pre>")
            continue

        # table (header row | ... | followed by a |---| separator)
        if "|" in line and i + 1 < n and re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]*$", lines[i+1]):
            def cells(row):
                row = row.strip()
                if row.startswith("|"): row = row[1:]
                if row.endswith("|"): row = row[:-1]
                return [c.strip() for c in row.split("|")]
            header = cells(line)
            i += 2
            body = []
            while i < n and "|" in lines[i] and lines[i].strip():
                body.append(cells(lines[i])); i += 1
            t = ["<table><thead><tr>"] + [f"<th>{inline(c)}</th>" for c in header] + ["</tr></thead><tbody>"]
            for r in body:
                t.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            t.append("</tbody></table>")
            out.append("".join(t))
            continue

        # blockquote (consecutive > lines)
        if line.startswith(">"):
            buf = []
            while i < n and lines[i].startswith(">"):
                buf.append(lines[i][1:].lstrip()); i += 1
            inner = md_to_html("\n".join(buf))
            out.append("<blockquote>" + inner + "</blockquote>")
            continue

        # headings
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = len(m.group(1)); out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            i += 1; continue

        # horizontal rule
        if re.match(r"^---+\s*$", line):
            out.append("<hr>"); i += 1; continue

        # standalone image line -> figure (optional *italic caption* on next line)
        im = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", line)
        if im:
            alt, src = im.group(1), im.group(2)
            i += 1
            cap = ""
            if i < n and re.match(r"^\*[^*].*\*\s*$", lines[i]):
                cap = f"<figcaption>{inline(lines[i].strip().strip('*'))}</figcaption>"
                i += 1
            out.append(f'<figure><img src="{html.escape(src)}" alt="{html.escape(alt)}" loading="lazy">{cap}</figure>')
            continue

        # unordered list
        if re.match(r"^\s*[-*]\s+", line):
            items = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i])); i += 1
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>")
            continue

        # ordered list
        if re.match(r"^\s*\d+\.\s+", line):
            items = []
            while i < n and re.match(r"^\s*\d+\.\s+", lines[i]):
                items.append(re.sub(r"^\s*\d+\.\s+", "", lines[i])); i += 1
            out.append("<ol>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ol>")
            continue

        # blank
        if not line.strip():
            i += 1; continue

        # paragraph (gather until blank/structural)
        buf = [line]; i += 1
        while i < n and lines[i].strip() and not re.match(r"^(#|>|```|\s*[-*]\s|\s*\d+\.\s|---+\s*$)", lines[i]) and "|" not in lines[i]:
            buf.append(lines[i]); i += 1
        out.append("<p>" + inline(" ".join(buf)) + "</p>")

    return "\n".join(out)


def nav_html(active_file: str) -> str:
    items = []
    for label, fn, _ in PAGES:
        cls = ' class="active"' if fn == active_file else ""
        items.append(f'<a href="{fn}"{cls}>{html.escape(label)}</a>')
    return (
        '<div class="nav-group">Guide</div>' + "".join(items[:4]) +
        '<div class="nav-group">Reference</div>' + "".join(items[4:]) +
        '<div class="nav-group">Repo</div>'
        '<a href="https://github.com/dkontango/spacelift-gitops-demo">GitHub mirror</a>'
        '<a href="https://git.konoss.org/kadmin/spacelift-gitops-demo">Forgejo (canonical)</a>'
    )


TEMPLATE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Spacelift GitOps Guide</title>
<link rel="stylesheet" href="assets/style.css">
</head><body><div class="layout">
<nav class="sidebar">
  <p class="brand">Spacelift <span>GitOps</span> Guide</p>
  <p class="brand-sub">Forgejo → GitHub → Spacelift → AWS</p>
  {nav}
</nav>
<main class="content">
{body}
<div class="footer">Deployed via Spacelift → S3 static website. Source of truth: Forgejo <code>git.konoss.org/kadmin/spacelift-gitops-demo</code>, mirrored to GitHub.</div>
</main></div></body></html>"""


# Full-width landing shell: a top nav bar instead of a docs sidebar, so the
# home page reads like a landing page while the guide pages keep the sidebar.
LANDING_TEMPLATE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="A hands-on Spacelift GitOps demo: pull-request previews, OPA policy guardrails, and keyless AWS deploys with OpenTofu — driven from an on-prem Forgejo repo mirrored to GitHub.">
<link rel="stylesheet" href="assets/style.css">
</head><body class="landing">
<header class="topbar">
  <div class="topbar-inner">
    <a class="brand" href="index.html">Spacelift <span>GitOps</span> Demo</a>
    <nav class="topnav">
      <a href="#why">Why Spacelift</a>
      <a href="#how">How it works</a>
      <a href="by-hand.html">Guide</a>
      <a href="walkthrough.html">Walkthrough</a>
      <a href="#contact" class="topnav-cta">Contact</a>
    </nav>
  </div>
</header>
<main class="landing-main">
{body}
</main>
<footer class="landing-footer">
  <div class="lf-inner">
    <div>
      <strong>Spacelift GitOps Demo</strong><br>
      <span class="lf-muted">Deployed by the pipeline it documents — Spacelift → S3, and GitHub Pages.</span>
    </div>
    <div class="lf-links">
      <a href="https://spacelift.io/" target="_blank" rel="noopener">spacelift.io</a>
      <a href="https://github.com/dkontango/spacelift-gitops-demo" target="_blank" rel="noopener">GitHub</a>
      <a href="https://git.konoss.org/kadmin/spacelift-gitops-demo" target="_blank" rel="noopener">Forgejo (canonical)</a>
    </div>
  </div>
</footer>
</body></html>"""


INDEX_BODY = """
<section class="lp-hero">
  <div class="lp-hero-inner">
    <span class="lp-eyebrow">OpenTofu · AWS · OPA · Keyless OIDC</span>
    <h1>Ship infrastructure with guardrails, not guesswork.</h1>
    <p class="lp-sub">A working, end-to-end <strong>Spacelift GitOps</strong> demo: every pull request gets a plan preview, an <strong>OPA policy</strong> blocks risky changes before they merge, and deploys to AWS run <strong>keyless</strong> — driven from an on-prem Forgejo repo mirrored to GitHub.</p>
    <div class="lp-cta-row">
      <a class="lp-btn lp-btn-primary" href="#contact">Get in touch</a>
      <a class="lp-btn lp-btn-ghost" href="walkthrough.html">See the 17-step walkthrough →</a>
    </div>
    <div class="lp-pipeline" aria-label="pipeline">
      <span>Forgejo</span><i>→</i><span>GitHub</span><i>→</i><span>Spacelift preview</span><i>→</i><span>OPA policy</span><i>→</i><span>AWS deploy</span>
    </div>
  </div>
</section>

<section class="lp-section">
  <div class="lp-benefits">
    <div class="lp-benefit"><div class="lp-ic">🔀</div><h3>PR-driven previews</h3><p>Open a pull request and Spacelift posts a plan as a status check — see exactly what will change before anything is applied.</p></div>
    <div class="lp-benefit"><div class="lp-ic">🛡️</div><h3>Policy as code</h3><p>A Rego <code>plan-block-public-s3</code> guardrail denies a public S3 bucket in the preview. The bad PR goes red; fix it and it turns green.</p></div>
    <div class="lp-benefit"><div class="lp-ic">🔑</div><h3>Keyless AWS</h3><p>Deploys authenticate via OIDC / AssumeRole. No static credentials stored in Spacelift, in a Context, or anywhere else.</p></div>
    <div class="lp-benefit"><div class="lp-ic">🧰</div><h3>Tool-agnostic</h3><p>The same loop works with Terraform, OpenTofu, Pulumi, CloudFormation, or Kubernetes — standardize the workflow, not the tool.</p></div>
  </div>
</section>

<section class="lp-section lp-alt" id="why">
  <div class="lp-narrow">
    <h2 class="lp-h2">Why a vendor-agnostic tool for end-to-end CI/CD</h2>
    <p class="lp-lede">This demo happens to use OpenTofu and AWS — but the point of <a href="https://spacelift.io/" target="_blank" rel="noopener">Spacelift</a> is that it locks you to neither. Traditional pipelines were built for application code; infrastructure needs a system that understands <em>state</em>. In Spacelift's words: <a href="https://spacelift.io/" target="_blank" rel="noopener">"Traditional CI/CD doesn't work for infrastructure"</a> — you want <a href="https://spacelift.io/" target="_blank" rel="noopener">"workflows that understand state, not hacked-together jobs and scripts."</a></p>
  </div>
  <div class="lp-cards">
    <div class="lp-card"><h3>One orchestrator, every tool</h3><p>Spacelift advertises <a href="https://spacelift.io/" target="_blank" rel="noopener">"first-class support for Terraform, OpenTofu, CloudFormation, Pulumi, and Kubernetes"</a> (plus Terragrunt and Ansible). The PR-preview → policy → deploy loop shown here works whichever IaC you standardize on — no rewrite when the tool changes.</p></div>
    <div class="lp-card"><h3>Understands your infrastructure</h3><p><a href="https://spacelift.io/" target="_blank" rel="noopener">"Spacelift understands your stacks, dependencies, state, and resources, giving you one place to manage every part of your infrastructure pipeline."</a> That's the difference between orchestration and a pile of CI jobs.</p></div>
    <div class="lp-card"><h3>Policy as code, across the board</h3><p><a href="https://spacelift.io/" target="_blank" rel="noopener">"Define OPA-based policies for plans, approvals, notifications, and security controls."</a> The <code>plan-block-public-s3</code> guardrail here is exactly that — a Rego Plan policy that blocks a risky change in the PR preview.</p></div>
    <div class="lp-card"><h3>Speed <em>and</em> control</h3><p>Spacelift's own framing: <a href="https://spacelift.io/" target="_blank" rel="noopener">"The speed developers demand. The control platform teams require."</a> Self-service <a href="https://spacelift.io/" target="_blank" rel="noopener">"Golden Paths via Blueprints, not Confluence pages"</a>, with <a href="https://spacelift.io/" target="_blank" rel="noopener">"guardrails enforced by policy as code."</a></p></div>
  </div>
  <div class="lp-narrow">
    <blockquote class="lp-quote"><a href="https://spacelift.io/" target="_blank" rel="noopener">"Ship infrastructure as fast as developers code"</a> — <a href="https://spacelift.io/" target="_blank" rel="noopener">"Spacelift fuses AI, IaC, and GitOps pipelines, so developers ship fast, and platform teams stay in control."</a></blockquote>
    <p class="lp-fine">Quoted phrases are Spacelift's own marketing language, from <a href="https://spacelift.io/" target="_blank" rel="noopener">spacelift.io</a> and its <a href="https://spacelift.io/pricing" target="_blank" rel="noopener">pricing page</a>, cited to keep this value proposition consistent with the vendor's. Drift detection and stack dependencies referenced in the demo are Starter+ features per that pricing page.</p>
  </div>
</section>

<section class="lp-section" id="how">
  <div class="lp-narrow">
    <h2 class="lp-h2">How it works</h2>
    <p class="lp-lede">The whole loop, proven live in this demo — from a push to an on-prem Forgejo repo all the way to a real S3 bucket in AWS.</p>
  </div>
  <ol class="lp-steps">
    <li><span class="lp-step-n">1</span><div><strong>Push only to Forgejo.</strong> A push-mirror (<code>sync_on_commit</code>) propagates to GitHub automatically.</div></li>
    <li><span class="lp-step-n">2</span><div><strong>Open a PR on GitHub.</strong> Spacelift previews the plan and posts it as a status check.</div></li>
    <li><span class="lp-step-n">3</span><div><strong>The policy guards it.</strong> An OPA Plan policy denies a public S3 bucket — the check goes red on the PR.</div></li>
    <li><span class="lp-step-n">4</span><div><strong>Fix, merge, deploy.</strong> Push the fix → the check passes → merge → Spacelift deploys to AWS via keyless OIDC.</div></li>
  </ol>
  <div class="lp-video">
    <video controls preload="metadata" poster="assets/steps/step-00-architecture.png">
      <source src="assets/workflow.mp4" type="video/mp4">
      Your browser doesn't support embedded video — <a href="https://github.com/dkontango/spacelift-gitops-demo/blob/main/docs/recording/workflow.mp4">download the walkthrough</a>.
    </video>
    <p class="lp-fine">A 68-second screen recording of all 17 steps, captured live from the real AWS, Spacelift, and GitHub consoles (account IDs and ARNs redacted).</p>
  </div>
  <div class="lp-narrow lp-guide-links">
    <a class="lp-btn lp-btn-ghost" href="by-hand.html">Onboarding — by hand</a>
    <a class="lp-btn lp-btn-ghost" href="with-ai.html">Onboarding — with an AI agent</a>
    <a class="lp-btn lp-btn-ghost" href="troubleshooting.html">Troubleshooting: AWS creds</a>
  </div>
</section>

<section class="lp-section lp-alt" id="contact">
  <div class="lp-narrow">
    <h2 class="lp-h2">Contact us</h2>
    <p class="lp-lede">Questions about this demo, or about running Spacelift for your own end-to-end CI/CD? Drop your email and we'll send a confirmation and follow up.</p>
    <p class="lp-fine">Fittingly, the contact flow is itself GitHub-native: submitting opens a prefilled GitHub <em>issue</em> — no credential in this page — and a GitHub Actions workflow reads our SMTP secret from <strong>Actions Secrets</strong> and sends the email, then closes the issue. Static site → GitHub → Actions (secret stays server-side) → real email: the same secrets-never-in-the-client pattern this whole demo is about.</p>
  </div>

<form id="contact-form" class="contact-form" novalidate>
  <div class="cf-row">
    <label for="cf-name">Name</label>
    <input id="cf-name" name="name" type="text" autocomplete="name" maxlength="120" placeholder="Your name">
  </div>
  <div class="cf-row">
    <label for="cf-email">Email <span class="cf-req">*</span></label>
    <input id="cf-email" name="email" type="email" autocomplete="email" required maxlength="254" placeholder="you@company.com">
    <small class="cf-err" id="cf-email-err" hidden>Please enter a valid email address.</small>
  </div>
  <div class="cf-row">
    <label for="cf-message">Message</label>
    <textarea id="cf-message" name="message" rows="3" maxlength="2000" placeholder="Optional — what would you like to know?"></textarea>
  </div>
  <input type="text" name="website" id="cf-website" tabindex="-1" autocomplete="off" aria-hidden="true" style="position:absolute;left:-9999px;width:1px;height:1px;opacity:0">
  <div class="cf-actions">
    <button type="submit" id="cf-submit" class="cf-btn">Send</button>
    <span class="cf-status" id="cf-status" role="status" aria-live="polite"></span>
  </div>
</form>

<script>
(function(){
  // GitHub-native contact: the form opens a prefilled Issue (labeled "contact")
  // in the repo. A GitHub Actions workflow then reads the SMTP secret from
  // Actions Secrets and emails the submitter + the team — no server of ours and
  // no credential in this page. Anonymous fallback: a mailto: to the same inbox.
  var ISSUE_BASE = "https://github.com/dkontango/spacelift-gitops-demo/issues/new";
  var ADMIN_MAILTO = "admin@kontango.us";
  var form = document.getElementById('contact-form');
  if (!form) return;
  var emailEl = document.getElementById('cf-email');
  var emailErr = document.getElementById('cf-email-err');
  var statusEl = document.getElementById('cf-status');
  var btn = document.getElementById('cf-submit');
  var RE = /^[A-Za-z0-9._%+\\-]+@[A-Za-z0-9.\\-]+\\.[A-Za-z]{2,}$/;

  function validEmail(v){ return v.length <= 254 && RE.test(v); }
  function setStatus(html, kind){ statusEl.innerHTML = html; statusEl.className = 'cf-status' + (kind ? ' cf-'+kind : ''); }

  emailEl.addEventListener('input', function(){
    if (!emailEl.value || validEmail(emailEl.value.trim())) { emailErr.hidden = true; emailEl.classList.remove('cf-invalid'); }
  });

  form.addEventListener('submit', function(e){
    e.preventDefault();
    var email = emailEl.value.trim();
    if (!validEmail(email)) { emailErr.hidden = false; emailEl.classList.add('cf-invalid'); emailEl.focus(); return; }
    if (document.getElementById('cf-website').value) { return; } // honeypot
    var name = document.getElementById('cf-name').value.trim() || '(not given)';
    var message = document.getElementById('cf-message').value.trim() || '(no message)';

    // Body uses "Field: value" lines the mailer workflow parses.
    var body = "Email: " + email + "\\nName: " + name + "\\n\\nMessage:\\n" + message +
               "\\n\\n---\\n_Submitted from the Spacelift GitOps demo site. A GitHub Actions " +
               "workflow will email a confirmation and close this issue automatically._";
    var url = ISSUE_BASE +
      "?title=" + encodeURIComponent("Contact: " + email) +
      "&labels=" + encodeURIComponent("contact") +
      "&body=" + encodeURIComponent(body);

    window.open(url, "_blank", "noopener");
    var mailto = "mailto:" + ADMIN_MAILTO +
      "?subject=" + encodeURIComponent("Contact from the Spacelift GitOps demo") +
      "&body=" + encodeURIComponent("From: " + name + " <" + email + ">\\n\\n" + message);
    setStatus("Opening GitHub to submit your message — click <strong>Submit new issue</strong> and " +
      "we'll email a confirmation to <strong>" + email + "</strong> automatically. " +
      "Not on GitHub? <a href=\\"" + mailto + "\\">Email us directly</a> instead.", 'ok');
  });
})();
</script>
</section>
"""


WIZARD_BODY = r"""
<div class="wiz-head">
  <h1>Illustrated Walkthrough</h1>
  <p>Swipe or use the arrows / keyboard (← →) to step through the whole workflow — AWS setup, the Spacelift integration, creating a stack, deploying, and the OPA policy blocking a bad change in a pull request.</p>
  <p class="wiz-note">Live screenshots have AWS account IDs and ARNs blacked out. The AWS-console steps are shown as labeled diagrams; everything on the Spacelift side is a real, redacted screenshot.</p>
</div>

<div class="wizard" id="wizard">
  <div class="wiz-stage">
    <button class="wiz-arrow wiz-prev" id="wizPrev" aria-label="Previous step">&#8249;</button>
    <figure class="wiz-slide" id="wizSlide">
      <div class="wiz-caption-top"><span class="wiz-counter" id="wizCounter"></span><span class="wiz-title" id="wizTitle"></span></div>
      <div class="wiz-imgwrap"><img id="wizImg" alt=""></div>
      <figcaption id="wizCap"></figcaption>
    </figure>
    <button class="wiz-arrow wiz-next" id="wizNext" aria-label="Next step">&#8250;</button>
  </div>
  <div class="wiz-progress"><div class="wiz-bar" id="wizBar"></div></div>
  <div class="wiz-dots" id="wizDots"></div>
</div>

<script>
(function(){
  var steps = __DATA__;
  var total = __TOTAL__;
  var idx = 0;

  var img = document.getElementById('wizImg');
  var title = document.getElementById('wizTitle');
  var cap = document.getElementById('wizCap');
  var counter = document.getElementById('wizCounter');
  var bar = document.getElementById('wizBar');
  var dotsEl = document.getElementById('wizDots');
  var slide = document.getElementById('wizSlide');

  // build dots
  for (var i=0;i<total;i++){
    var d = document.createElement('button');
    d.className='wiz-dot'; d.setAttribute('aria-label','Go to step '+(i+1));
    (function(n){ d.addEventListener('click', function(){ go(n); }); })(i);
    dotsEl.appendChild(d);
  }
  var dots = dotsEl.querySelectorAll('.wiz-dot');

  function render(){
    var s = steps[idx] || {title:'',img:'',cap:''};
    // fade
    slide.classList.remove('show');
    var pre = new Image();
    pre.onload = show; pre.onerror = show; pre.src = s.img;
    function show(){
      img.src = s.img; img.alt = s.title;
      title.innerHTML = s.title;
      cap.innerHTML = s.cap;
      counter.textContent = (idx+1)+' / '+total;
      bar.style.width = ((idx+1)/total*100)+'%';
      for (var i=0;i<dots.length;i++){ dots[i].classList.toggle('active', i===idx); }
      requestAnimationFrame(function(){ slide.classList.add('show'); });
    }
    if (location.hash !== '#step-'+(idx+1)) history.replaceState(null,'','#step-'+(idx+1));
  }
  function go(n){ idx = Math.max(0, Math.min(total-1, n)); render(); }
  function next(){ go(idx+1); }
  function prev(){ go(idx-1); }

  document.getElementById('wizNext').addEventListener('click', next);
  document.getElementById('wizPrev').addEventListener('click', prev);
  document.addEventListener('keydown', function(e){
    if (e.key==='ArrowRight') next();
    else if (e.key==='ArrowLeft') prev();
  });

  // swipe / drag
  var startX=null, dragging=false;
  function down(x){ startX=x; dragging=true; slide.style.transition='none'; }
  function move(x){ if(!dragging) return; slide.style.transform='translateX('+((x-startX)*0.4)+'px)'; }
  function up(x){ if(!dragging) return; dragging=false; slide.style.transition='';
    var dx = x-startX; slide.style.transform='';
    if (dx < -50) next(); else if (dx > 50) prev();
    startX=null;
  }
  slide.addEventListener('touchstart', function(e){ down(e.touches[0].clientX); }, {passive:true});
  slide.addEventListener('touchmove', function(e){ move(e.touches[0].clientX); }, {passive:true});
  slide.addEventListener('touchend', function(e){ up((e.changedTouches[0]||{}).clientX||startX); });
  slide.addEventListener('mousedown', function(e){ down(e.clientX); e.preventDefault(); });
  window.addEventListener('mousemove', function(e){ move(e.clientX); });
  window.addEventListener('mouseup', function(e){ up(e.clientX); });

  // deep link
  var m = (location.hash||'').match(/#step-(\d+)/);
  if (m){ idx = Math.max(0, Math.min(total-1, parseInt(m[1],10)-1)); }
  render();
})();
</script>
"""


def parse_walkthrough_steps():
    """Parse docs/illustrated-walkthrough.md into a list of {title, img, caption}.

    A step is: a line with an image `![alt](src)`, optionally preceded by the most
    recent `## heading` (title) and followed by an `*italic caption*` line.
    """
    src = os.path.join(ROOT, "docs/illustrated-walkthrough.md")
    with open(src, encoding="utf-8") as f:
        lines = f.read().split("\n")
    steps = []
    last_h2 = None
    intro = None  # the leading blockquote note, shown on the first slide
    i = 0
    while i < len(lines):
        line = lines[i]
        m2 = re.match(r"^##\s+(.*)$", line)
        if m2:
            last_h2 = m2.group(1).strip()
            i += 1; continue
        im = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", line)
        if im:
            img = im.group(2)
            cap = ""
            if i + 1 < len(lines) and re.match(r"^\*[^*].*\*\s*$", lines[i + 1]):
                cap = lines[i + 1].strip().strip("*")
                i += 1
            title = last_h2 or "The pipeline"
            if img.strip():
                steps.append({"title": title, "img": img, "caption": cap})
            last_h2 = None
        i += 1
    return steps


def wizard_body():
    steps = parse_walkthrough_steps()
    # JSON-ish data array for the client.
    def esc(s):
        return (s or "").replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
    data = "[" + ",".join(
        "{title:'%s',img:'%s',cap:'%s'}" % (esc(inline_text(s["title"])), esc(s["img"]), esc(inline_text(s["caption"])))
        for s in steps
    ) + "]"
    total = len(steps)
    return WIZARD_BODY.replace("__DATA__", data).replace("__TOTAL__", str(total))


def inline_text(s):
    """Convert a bit of inline markdown (code/bold) to safe HTML for the wizard."""
    s = html.escape(s or "", quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    return s


def build():
    # Ship the walkthrough video with the site so it's same-origin on Pages/S3
    # (Pages publishes only site/). Copy it into site/assets/ if present.
    import shutil
    vid = os.path.join(ROOT, "docs/recording/workflow.mp4")
    if os.path.exists(vid):
        shutil.copyfile(vid, os.path.join(SITE, "assets", "workflow.mp4"))
        print("copied workflow.mp4 -> site/assets/")

    for label, fn, src in PAGES:
        landing = src is None
        if landing:
            # Contact form is GitHub-native (opens an Issue → Actions mailer);
            # the old __CONTACT_ENDPOINT__ placeholder is gone but replace() is
            # kept as a harmless no-op in case the self-hosted path is restored.
            body = INDEX_BODY.replace("__CONTACT_ENDPOINT__", CONTACT_ENDPOINT)
            title = "Spacelift GitOps Demo — PR previews, OPA guardrails, keyless AWS"
        elif src == "WIZARD":
            body = wizard_body(); title = "Illustrated Walkthrough"
        else:
            with open(os.path.join(ROOT, src), encoding="utf-8") as f:
                md = f.read()
            body = md_to_html(md); title = label
        if landing:
            out_html = LANDING_TEMPLATE.format(title=html.escape(title), body=body)
        else:
            out_html = TEMPLATE.format(title=html.escape(title), nav=nav_html(fn), body=body)
        with open(os.path.join(SITE, fn), "w", encoding="utf-8") as f:
            f.write(out_html)
        print("wrote", fn)


if __name__ == "__main__":
    build()
