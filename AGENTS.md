# AGENTS.md — Context for an AI Agent Driving the Spacelift Onboarding

You are an AI coding agent helping a human onboard to **Spacelift** and complete
its in-app tutorials (the GitOps workflow). This file tells you exactly what to
do, what the real object names are, and the pitfalls that will bite you. Read it
fully before acting. It is deliberately prescriptive.

> This file is auto-read by agents that honor `AGENTS.md` (and pointed to by
> `CLAUDE.md`). Human-readable versions of everything here live in
> `docs/onboarding-by-hand.md` and `docs/onboarding-with-ai.md`.

---

## 0. THE ONE RULE — pin the tuple before doing anything

Before you run, debug, or click anything, establish and repeat back this tuple.
Almost every failure in this project came from the human and the agent being
correct about **different** objects:

```
(stack name, repository, project root, IAM role ARN, cloud-integration name)
```

You and the human must agree on all five. Never debug by name alone — Spacelift
auto-generates opaque names (see §2) that tell you nothing about which repo or
role they use.

---

## 1. SESSION MANAGEMENT — read this before you open a browser

**Spacelift allows only ONE active session at a time.** The signup/login UI
literally shows a **"Multi-session disabled"** control. Logging in through one
channel invalidates the others:

- If you (the agent) log into Spacelift in an **automation browser (Playwright)**,
  you will **kick the human out of their own Spacelift web session**, and vice
  versa. Only one of you can be logged in at once.
- The same applies to `spacectl` / CLI / `terraform login`: authenticating there
  can invalidate the web session.

**Therefore, decide up front who holds the session:**

- **Agent-drives (Playwright) mode:** the human must NOT be logged into Spacelift
  in their own browser while you drive. Tell them to log out (or expect to be
  logged out). You hold the single session.
- **Human-drives mode:** you do NOT open Spacelift in a browser at all. You do
  the git/API/file work; the human clicks the Spacelift UI. Never open a
  Spacelift session in this mode — you'll evict them.

Confirm the mode with the human before touching Spacelift.

---

## 2. EXACT NAMING — use what Spacelift actually generates/expects

Do not invent your own parallel names. Spacelift and its tutorials use specific
literals; mismatched names are how the human and agent diverge.

**Spacelift auto-generates stack and integration names** — opaque two/three-word
handles, e.g.:
- Stacks: `Prime Apollo 45`
- AWS integrations: `Viking Terminal AWS`

These names encode **nothing** about their repo or role. When the human says
"the stack," get its exact name and its tuple (§0) — don't assume.

**The Foundations tutorial uses these literals** (match them exactly):
- Resource: `resource "random_pet" "name"` (the starter resource)
- Resource: `resource "aws_s3_bucket" "orbit_storage"` with
  `bucket_prefix = "orbit-storage-"`
- Data source: `data "aws_caller_identity" "current"`, output `aws_account_id`
- Suggested IAM role name: `spacelift-orbit-labs-role`
- Tutorial tags: `mission = "First Launch"`, `project = "Orbit-labs"`,
  `managedBy = "Spacelift"`

**AWS OIDC / AssumeRole facts (us.spacelift.io):**
- Spacelift principal AWS account: **`577638371743`** (EU/spacelift.io:
  `324880187172`)
- ExternalId condition: `StringLike` on `sts:ExternalId` = `<account-name>@*`
- `sts:TagSession` must be its **own** statement (no ExternalId condition)
- The Role ARN must start with **`arn:`** — a missing prefix (`aws:iam::…`) is a
  common paste error that surfaces as a (misleading) "trust relationship" error.

---

## 3. WHERE THE TUTORIAL LIVES

After creating a Spacelift account (free trial, sign up **with GitHub**), the
in-app tutorials are the **Foundations** guides, reached from **LaunchPad** or
the **Assistant panel** on a stack page. The two guides you'll complete:
1. **Credentials, Not Secrets — AWS Integration** (8 steps) — wire keyless AWS.
2. **First Launch — Deploy Real Infrastructure** (7 steps) — deploy a real S3
   bucket, then flip on autodeploy.
There is also a **Guardrails — Enforce Policy Rules** guide for policies.

Each guide step has **Next step** / **Previous step** / **Complete** buttons and
a progress bar (e.g. "3/7"). A step often gates on "a new run was triggered on
your stack."

---

## 4. STEP-BY-STEP (what you actually do)

Assume the git repo is `dkontango/spacelift-gitops-demo` (canonical on **Forgejo
`git.konoss.org/kadmin/spacelift-gitops-demo`**, push-mirrored to GitHub). Push
**only to Forgejo**; verify GitHub caught up with `git ls-remote github <branch>`.

1. **Confirm mode + session** (§1) and the **tuple** (§0).
2. **AWS prerequisites** (one-time): create the OIDC provider + IAM role via
   `bootstrap/` OpenTofu (least-priv) or `bootstrap-tutorial-role/` (the
   tutorial's S3+EC2 FullAccess `spacelift-orbit-labs-role`). Apply with admin
   AWS keys pulled from the secrets store; never store static keys in Spacelift.
3. **Cloud integration:** in Spacelift add the AWS integration with the role ARN.
   Leave **"Assume role on worker" = No**, **"Enable tag session" = Yes**.
   If attach fails with "configure trust relationship": (a) verify the ARN starts
   with `arn:`; (b) wait ~60s for IAM propagation and retry — do NOT rewrite a
   correct trust policy chasing a lag.
4. **Attach the integration to the specific stack** (Stack → Settings →
   Integrations). "Exists in the account" ≠ "attached to this stack." The error
   `no valid credential sources for Terraform AWS Provider` almost always means
   this attachment is missing.
5. **Confirm the stack's repo/project-root contains the starter code**
   (`random_pet`, `main.tf`). If the repo is empty/placeholder, the tutorial's
   "edit main.tf" step cannot work and the failure will look like an auth error.
6. **Follow the Foundations guide steps.** Edit files, commit, push to Forgejo,
   watch the run. With autodeploy **off**, runs stop at **UNCONFIRMED** for
   manual **Confirm** — that's the approval gate, not an error.
7. **Policies (Guardrails):** create a Plan policy; attach it to the stack. To
   fill the Rego editor (Monaco) via Playwright, use
   `page.keyboard.insertText(...)` — normal paste/typing corrupts it
   (auto-indent/auto-close). Then demonstrate a PR that flips a bucket public →
   the policy **denies** it in the PR preview.

---

## 5. RUN-QUEUE + BUTTON PITFALLS

- Spacelift runs blocking (tracked) runs **one at a time** per stack. A prior run
  left at **UNCONFIRMED** blocks new runs. Confirm or Discard it to release the
  queue.
- **Confirm** and **Discard** sit adjacent and the DOM shifts. Re-locate the
  exact button immediately before clicking; never click a
  constructive/destructive pair from a stale element reference.
- After every `git push`, verify the remote HEAD (`git ls-remote`). "Push
  succeeded" on a diverged local branch does not mean it landed where you think.

---

## 6. WHAT SUCCESS LOOKS LIKE

- A run authenticates to AWS via OIDC/AssumeRole and resolves
  `data.aws_caller_identity.current` to the account id (no static creds).
- A PR that makes a bucket public is **denied** by the Plan policy in the preview
  (the check fails on the policy-bearing stack, passes on one without it).
- Merge to the default branch deploys; with autodeploy on, a follow-up push
  applies without a manual Confirm.

If you hit an error not covered here, map it to §2–§5 before proposing a fix —
the message usually names a symptom, not the cause.
