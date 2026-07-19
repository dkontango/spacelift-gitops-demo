# Spacelift Onboarding — With an AI Agent

How to complete the same Spacelift GitOps workflow by directing an AI coding
agent. There are **two sub-modes**, and choosing correctly up front is the whole
game because of Spacelift's single-session limit.

> **Point your agent at [`AGENTS.md`](../AGENTS.md)** first — it is the machine-
> readable context (tuple rules, exact naming, session constraint, step-by-step,
> pitfalls). This page is the human's operating manual for working alongside it.

---

## ⚠️ Session management decides your mode

**Spacelift allows only ONE active session at a time** (the login UI shows
"Multi-session disabled"). Logging in one place invalidates the others. This
directly shapes how you use an agent:

| Mode | Who holds the Spacelift session | You must… |
|---|---|---|
| **A. Agent drives (Playwright)** | the **agent's** automation browser | **log out** of Spacelift in your own browser; the agent's browser is the single session |
| **B. Agent assists (no Playwright)** | **you** (human), in your browser | tell the agent **not** to open Spacelift; it does git/API/file work only |

If both you and a Playwright agent try to be logged in, you'll keep evicting each
other. Pick one holder of the session.

---

## Mode A — Agent drives via Playwright (or equivalent)

The agent clicks through the Spacelift and AWS UIs itself using browser
automation (Playwright MCP, Puppeteer, Selenium, etc.).

**Setup**
1. Give the agent `AGENTS.md`.
2. **Log yourself out of Spacelift** (Mode A holds the single session).
3. Provide the agent access to: the git repo, AWS credentials (ideally via a
   secrets store, not pasted), and the browser-automation tool.

**What the agent does** (mirrors `AGENTS.md` §4): create/verify the OIDC role,
create the AWS integration, **attach it to the stack**, follow the Foundations
guides (edit → push to Forgejo → watch run → Confirm), and attach + demonstrate
the Plan policy.

**Playwright-specific tips to give the agent**
- **Human MFA/OAuth gates:** logging into GitHub/AWS may hit 2FA or a CAPTCHA the
  agent can't solve. Be ready to complete that one step, or pre-authenticate the
  automation browser.
- **Monaco (Rego) editor:** normal paste/typing corrupts it (auto-indent/auto-
  close, or grabs the wrong OS clipboard). The reliable method is
  `page.keyboard.insertText(...)` via the raw Playwright API — set the whole
  policy body in one shot, then verify the character count.
- **Adjacent Confirm/Discard buttons + shifting DOM:** the agent must re-locate
  the exact button immediately before clicking; a stale element reference caused
  a Confirm-instead-of-Discard slip in our runs.
- **Toggles intercept clicks:** styled switches (Autodeploy, Tag session) often
  reject a direct checkbox click — click the label wrapper, or remove the stray
  overlay first.

**Your job in Mode A:** clear human-only gates (MFA), make decisions the agent
surfaces (which role, public vs private repo), and sanity-check the tuple it
reports.

---

## Mode B — Agent assists, human drives the UI (no Playwright)

The agent never opens Spacelift. It does the parts it's good at — writing the
Terraform/Rego, running git, calling APIs, applying the OIDC bootstrap — and
hands **you** precise click instructions for the Spacelift/AWS UI. **You** hold
the single Spacelift session.

**Division of labor**
- **Agent:** authors `main.tf` changes, the Rego policy, the OIDC bootstrap
  OpenTofu; runs `tofu`/`git`; pushes to Forgejo; verifies the GitHub mirror; and
  gives you exact, named steps ("Stack *Prime Apollo 45* → Settings → Integrations
  → Attach → select *Viking Terminal AWS*").
- **You:** perform each Spacelift/AWS click, then paste back the non-secret result
  (a Role ARN, a run state, an error) so the agent can proceed.

**Why this is often the better mode:** no session eviction, no CAPTCHA problem,
and you build hands-on familiarity for narrating a demo — while the agent removes
all the boilerplate (Terraform, Rego, git hygiene, the OIDC trust policy).

---

## The kickoff prompt (either mode)

Paste this to the agent (it complements `AGENTS.md`):

> "We're onboarding to Spacelift. First state the tuple — stack name, repository,
> project root, IAM role ARN, cloud-integration name — and confirm the
> integration is attached to that exact stack and the repo contains the starter
> code. Tell me whether we're in Mode A (you drive via Playwright — I'll log out
> of Spacelift) or Mode B (I drive the UI — you never open Spacelift). Use
> OIDC/AssumeRole, no static keys. us.spacelift.io principal is 577638371743; the
> role trust policy needs a separate TagSession statement; verify the Role ARN
> starts with `arn:`. If you hit 'no valid credential sources', check per-stack
> attachment first. If you hit 'configure trust relationship', check the ARN
> shape and wait 60s for IAM propagation before editing the trust policy. Push
> only to Forgejo and verify GitHub mirrored. Report the tuple and the remote
> HEAD after every push."

---

## Pitfalls unique to AI-assisted onboarding (why this guide exists)

Every one of these actually happened while building this repo:

1. **Two universes.** The human's stack watched an empty placeholder repo while
   the agent's code lived in a different repo. Nothing converged until the tuple
   was pinned. → Always agree the `(stack, repo, project-root, role, integration)`
   tuple.
2. **"The integration is attached"** was true for one stack, not the one being
   pushed to → `no valid credential sources`. → Verify per-stack attachment.
3. **Console login mistaken for API keys.** An email+password can't drive the CLI.
   → Verify credential *format*; mint real `AKIA…` keys or use OIDC.
4. **Malformed Role ARN** (`aws:iam::…` missing `arn:`) surfaced as a "trust
   relationship" error. → Check the ARN shape first.
5. **IAM propagation lag** made a correct role fail attach for ~1 minute. → Retry,
   don't rewrite.
6. **Monaco editor** resisted paste. → `insertText`.
7. **Run-queue serialization** blocked new runs behind a stale UNCONFIRMED run. →
   Confirm/Discard the blocker.
8. **Diverged local branch** made "push succeeded" a lie. → Verify remote HEAD.

Full narratives: [`tutorial-incident-log.md`](tutorial-incident-log.md) and
[`troubleshooting-case-study.md`](troubleshooting-case-study.md).
