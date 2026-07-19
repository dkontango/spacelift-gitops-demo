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

# (nav label, output filename, source markdown or None for the hand-written index)
PAGES = [
    ("Overview", "index.html", None),
    ("Illustrated Walkthrough", "walkthrough.html", "docs/illustrated-walkthrough.md"),
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


INDEX_BODY = """
<div class="hero">
  <h1>Spacelift GitOps Onboarding Guide</h1>
  <p>A complete, click-by-click walkthrough of the Spacelift GitOps workflow — with two tracks: do it <strong>by hand</strong>, or let an <strong>AI agent</strong> drive. This very site was deployed by the pipeline it documents.</p>
</div>

<div class="cards">
  <div class="card"><h3><a href="by-hand.html">Onboarding — By Hand</a></h3><p>Full click-by-click for a human. Exact Spacelift names, where the Foundations tutorial lives, and the session &amp; naming callouts.</p></div>
  <div class="card"><h3><a href="with-ai.html">Onboarding — With AI</a></h3><p>Let an agent drive. Two sub-modes: <span class="tag">Playwright</span> (agent clicks the UI) vs <span class="tag">no-Playwright</span> (agent assists, you click).</p></div>
  <div class="card"><h3><a href="agents.html">AI Agent Context</a></h3><p>The <code>AGENTS.md</code> file you point your agent at — tuple rules, exact naming, session constraint, step-by-step.</p></div>
  <div class="card"><h3><a href="troubleshooting.html">Troubleshooting</a></h3><p>The written deliverable: fixing <code>no valid credential sources for Terraform AWS Provider</code>.</p></div>
</div>

<h2>Two things that cause the most confusion</h2>
<blockquote>
<p><strong>⚠️ One Spacelift session at a time.</strong> Spacelift allows only one active session per user (the login UI shows "Multi-session disabled"). Logging in via CLI or a second browser invalidates your web session. If an AI agent drives via its own browser, it will log you out — decide who holds the session before you start.</p>
</blockquote>
<blockquote>
<p><strong>⚠️ Names are opaque and specific.</strong> Spacelift auto-generates stack/integration names like <code>Prime Apollo 45</code> and <code>Viking Terminal AWS</code> — they tell you nothing about the repo or role. Always track the full tuple: <strong>(stack, repository, project root, IAM role ARN, integration name)</strong>. The tutorial code uses exact literals: <code>random_pet</code>, <code>aws_s3_bucket.orbit_storage</code>, <code>bucket_prefix = "orbit-storage-"</code>, role <code>spacelift-orbit-labs-role</code>.</p>
</blockquote>

<h2>The workflow, in one line</h2>
<p>Push <strong>only to Forgejo</strong> → the push-mirror propagates to GitHub → Spacelift previews every PR → an <strong>OPA Plan policy</strong> blocks a public S3 bucket in the preview → merge deploys to AWS via <strong>keyless OIDC</strong>.</p>
"""


def build():
    for label, fn, src in PAGES:
        if src is None:
            body = INDEX_BODY; title = "Overview"
        else:
            with open(os.path.join(ROOT, src), encoding="utf-8") as f:
                md = f.read()
            body = md_to_html(md); title = label
        out_html = TEMPLATE.format(title=html.escape(title), nav=nav_html(fn), body=body)
        with open(os.path.join(SITE, fn), "w", encoding="utf-8") as f:
            f.write(out_html)
        print("wrote", fn)


if __name__ == "__main__":
    build()
