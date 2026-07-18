# If You're Using an AI Agent to Onboard to Spacelift — An Explicit Guide

This whole environment was built by directing an AI coding agent (Claude)
through Spacelift, AWS, Forgejo, and GitHub. It worked — but the agent and the
human produced several real, confusing errors along the way, none of which were
Spacelift bugs. They were **coordination, naming, and credential** mistakes that
are specific to AI-assisted work.

This guide is the prescriptive version: **do these things, in this order, and
you will avoid every pitfall we hit.** It assumes you (a human) are directing an
agent that can edit files, run git, and click through web UIs.

---

## The one rule that prevents 80% of the pain

**Before running or debugging anything, pin and share the exact tuple:**

```
(stack name, repository, project root, IAM role, cloud-integration name)
```

The agent and you must be looking at the **same** five values. Almost every
error below came from the human and the agent being correct about *different*
objects. Say the tuple out loud; put it at the top of the task.

---

## Step-by-step, with the agent-specific guardrails

### 0. Decide the naming up front — don't let auto-names diverge
- Spacelift **auto-generates** stack and integration names ("Prime Apollo 45",
  "Viking Terminal AWS"). These names tell you **nothing** about which repo or
  role they use.
- An agent will **invent its own** parallel names (`spacelift-gitops-demo-*`,
  `aws-orbit-labs-role`). Left unchecked you get two naming universes for one
  intent.
- **Do:** rename stacks/integrations to something that encodes the repo/role, or
  at minimum have the agent record the tuple (above) for every object it creates.
  Never debug by name alone — names lie.

### 1. AWS credentials: console vs programmatic
- If someone hands the agent an **email + password**, that's a **console login**
  — it cannot drive the CLI, OpenTofu, or Spacelift. Programmatic keys look like
  `AKIA…` + a 40-char secret.
- **Do:** have the agent verify the credential *format* before using it, and mint
  real access keys from IAM → Security credentials → Create access key.
- **Better:** don't store static keys at all — use Spacelift's **OIDC /
  AssumeRole** integration so nothing long-lived is stored.

### 2. The IAM role trust policy — get the shape exactly right
For a public-worker AWS integration on **us.spacelift.io**, the role must trust:
```json
{ "Effect":"Allow", "Action":"sts:AssumeRole",
  "Principal":{"AWS":"577638371743"},
  "Condition":{"StringLike":{"sts:ExternalId":"<your-account>@*"}} }
```
plus a **separate** statement for `sts:TagSession` (no ExternalId condition) if
tag-session is enabled. (EU/`spacelift.io` uses principal `324880187172`.)

- **Pitfall:** the error `configure trust relationship section in your AWS
  account` is **overloaded**. It fires for a genuinely-wrong trust policy *and*
  for a **malformed Role ARN** (e.g. `aws:iam::…` missing the leading `arn:`) —
  the ARN, not the trust policy, was our actual bug once. Have the agent verify
  the ARN shape first.
- **Pitfall:** IAM changes are **eventually consistent**. A fresh role can fail
  the attach validation for a minute, then succeed on retry. Don't rewrite a
  correct trust policy chasing a propagation lag — wait ~60s and retry.

### 3. Attach the integration to the *stack* — not just the account
- `no valid credential sources for Terraform AWS Provider` almost always means
  the cloud integration exists but is **not attached to this specific stack**.
  Creating it at the account level is not enough.
- **Do:** have the agent open the stack → Settings → Integrations and confirm the
  cloud integration is attached **to that stack** before pushing IaC that needs
  AWS. "An integration is attached" and "this stack has it attached" are
  different claims — verify the second.

### 4. Confirm the stack's repo actually contains the code
- A stack points at `(repo, project root)`. If that repo is empty or a
  placeholder (ours was a README-only repo), the tutorial's "edit main.tf" step
  can't work and the failure looks like an auth error.
- **Do:** have the agent confirm the stack's repo/project-root contains the
  expected starter code (`random_pet`, `main.tf`, etc.) before editing anything.

### 5. Pushing policies into Spacelift's Monaco editor
- The Rego editor is a Monaco instance that **resists normal paste** via browser
  automation (auto-close/auto-indent corrupts the text; OS-clipboard paste can
  grab the wrong content).
- **What works:** drive the editor with Playwright's `keyboard.insertText()`
  (inserts text without firing per-key handlers) — set the value in one shot,
  then verify the character count. Or manage policies as code via Spacelift's
  Terraform provider and skip the editor entirely.

### 6. Run-queue serialization
- Spacelift runs blocking (tracked) runs **one at a time** per stack. A previous
  run left at **UNCONFIRMED** (autodeploy off) will **block** every new run
  behind it.
- **Do:** Confirm or Discard stale runs to release the queue. And beware: the
  **Confirm** and **Discard** buttons sit adjacent and the DOM shifts — re-locate
  the exact button immediately before clicking (the agent once hit Confirm
  instead of Discard because a ref moved). Never click a
  constructive/destructive pair from a stale reference.

### 7. Git hygiene with an agent
- "Push succeeded" against a **diverged local branch** does not mean the change
  is on the branch you think. Have the agent confirm the remote HEAD after every
  push (`git ls-remote`), and prefer fast-forward pushes.
- If you use a **Forgejo → GitHub push-mirror**, push **only** to Forgejo and
  verify GitHub caught up (`git ls-remote github <branch>`); don't push both and
  create divergence.

### 8. Autodeploy is a workflow switch, not a bug
- With **autodeploy off** (the default), every push stops at UNCONFIRMED for
  manual approval — that's not an error, it's the approval gate. Turn it **on**
  for fast iteration; keep it **off** for production. Tell the agent which mode
  you want so it doesn't "fix" a paused run that's working as designed.

---

## A ready-to-use kickoff prompt for the agent

> "We're onboarding to Spacelift. Before you touch anything, state the tuple:
> stack name, repository, project root, IAM role ARN, and cloud-integration
> name — and confirm the integration is attached to that exact stack and the
> repo contains the starter code. Use OIDC/AssumeRole (no static keys). The AWS
> principal for us.spacelift.io is 577638371743; the role trust policy needs a
> separate TagSession statement; verify the Role ARN starts with `arn:`. If you
> hit 'no valid credential sources', check per-stack attachment first. If you hit
> 'configure trust relationship', check the ARN shape and wait 60s for IAM
> propagation before editing the trust policy. Push only to Forgejo and verify
> GitHub mirrored. Report the tuple and the remote HEAD after every push."

Hand the agent that paragraph and it will sidestep every pitfall documented in
[`tutorial-incident-log.md`](tutorial-incident-log.md) and
[`troubleshooting-case-study.md`](troubleshooting-case-study.md).
