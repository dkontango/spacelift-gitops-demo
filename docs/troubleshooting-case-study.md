# Troubleshooting Case Study: A Real Error, Lived End to End

This is the centerpiece of the demo. The take-home asked two things: demonstrate
the GitOps workflow, and troubleshoot a prospect's error. Rather than invent a
hypothetical, we reproduced — accidentally and then deliberately — the **exact**
error the prospect reported, plus a second, subtler one. This document is the
honest, blow-by-blow account: what the error was, what inputs were given to the
AI agent (Claude) that caused it, why it's an issue, and how we resolved it.

**The framing that makes this valuable:** the whole environment was built by a
human directing an AI coding agent. The most instructive failure wasn't a
Spacelift bug — it was a **coordination failure between the human and the agent**
that produced the prospect's exact error message. That is precisely the class of
problem a Solutions Engineer is there to catch and explain.

---

## The error(s) we reproduced

### Error A — the prospect's exact error
```
configuring Terraform AWS Provider: no valid credential sources for Terraform
AWS Provider found.
```
Seen in a Spacelift run as:
```
Error: No valid credential sources found
  with provider["registry.opentofu.org/hashicorp/aws"]
  on providers.tf line 25, in provider "aws":
Error: failed to refresh cached credentials, no EC2 IMDS role found,
operation error ec2imds: GetMetadata, request canceled, context deadline exceeded
```

### Error B — the misleading trust-relationship error
```
unauthorized: you need to configure trust relationship section in your AWS account
```
Seen when attaching an AWS cloud integration to a stack.

Both are "credential" errors on the surface. Neither had the cause the message
implies. That's the lesson.

---

## What actually caused each error

There were **three distinct root causes**, and they stacked on top of each
other, which is why it took real diagnosis to separate them.

### Root cause 1 — the AWS integration was not attached to the stack (Error A)

Spacelift runs on a fresh cloud worker that inherits nothing. If no cloud
integration is **attached to the specific stack**, the AWS provider walks its
whole credential chain (env vars → shared config → assume-role → EC2 IMDS) and
finds nothing, then times out on IMDS — producing Error A verbatim.

Creating the integration at the account level is **not** enough. It must be
attached to each stack. This is the single most common cause of the prospect's
error, and we hit it live on the sandbox stack.

### Root cause 2 — a malformed Role ARN in the integration (Error B)

A second integration ("Viking Terminal AWS") was configured by hand with the
Role ARN:
```
aws:iam::193456333226:role/spacelift-orbit-labs-role      ← missing "arn:"
```
The leading `arn:` had been dropped when the value was pasted. Spacelift's
attach-time validation does a live `sts:AssumeRole`; an unresolvable ARN fails,
and Spacelift reports it as *"configure trust relationship"* — even though the
trust policy was perfectly correct. The message points you at the wrong thing.

### Root cause 3 — the AI agent and the human were working two different repos/stacks

This is the real story, and the most important one.

- The **human**, following Spacelift's in-app "Foundations" tutorial, was working
  on a stack called **`Prime Apollo 45`**, whose source repository is
  **`dkontango/7777MP`**.
- The **AI agent (Claude)** built and tested everything in a *different* repo,
  **`dkontango/spacelift-gitops-demo`**, driving the stacks
  `spacelift-gitops-demo-sandbox` / `-dev`.

`dkontango/7777MP` contains **only a `README.md`** — no `main.tf`, no
`random_pet`, no Terraform at all. So when the tutorial said *"edit main.tf to
add the AWS provider alongside your existing random_pet resource,"* there was
nothing to edit and nothing to run on that stack. Meanwhile every fix the agent
made landed in `spacelift-gitops-demo`, a repo `Prime Apollo 45` doesn't watch.

**Two parallel universes that never touched.** The tutorial "kept returning an
error" because the human's stack pointed at an empty repo, while the agent's
verified, working code lived somewhere the human's stack couldn't see.

---

## The exact inputs given to Claude that caused this

Being precise and honest about the agent's side, since that was the objective:

1. **"The aws integration is attached"** — given as fact. It was true for the
   *dev* stack, but **not** for the sandbox stack the tutorial was editing (Root
   cause 1). The agent took the statement at face value and pushed the
   tutorial's AWS-provider change, which then failed with Error A. *Lesson: "the
   integration exists" and "the integration is attached to THIS stack" are
   different claims; verify the second.*

2. **A pasted value that looked like AWS credentials but was a console login**
   (`admin@kontango.us` + a 20-char string). Treating it as programmatic keys
   would have produced Error A directly. The agent flagged the format mismatch
   instead of proceeding. *Lesson: console credentials ≠ programmatic
   credentials; the AWS provider can only use the latter.*

3. **A malformed Role ARN** (`aws:iam::…`, missing `arn:`) configured by hand in
   the Viking integration (Root cause 2), surfacing as the misleading Error B.

4. **No shared statement of which repo/stack was "the" tutorial target.** The
   agent assumed `spacelift-gitops-demo`; the human's tutorial stack pointed at
   `7777MP` (Root cause 3). Neither side stated the assumption, so both were
   "right" about different environments. *Lesson: pin the exact stack + repo
   before debugging a run — the run belongs to one specific (stack, repo,
   project-root) tuple.*

---

## Why this is an issue (the SE-relevant point)

- **Error messages name the symptom, not the cause.** "No valid credential
  sources" and "configure trust relationship" both point at credentials/trust,
  but the real causes were *integration-not-attached-to-stack*,
  *malformed-ARN*, and *wrong-repo*. A prospect will burn hours re-checking a
  trust policy that was never wrong.
- **The failure surfaced from coordination, not product defect.** In an
  AI-assisted workflow (which is now the default), the human and the agent can
  each be correct about a different environment. The mismatch produces real,
  confusing errors. Catching *that* is the SE skill.
- **The tutorial's happy path assumes the stack's repo already has the
  `random_pet` code.** When the stack points at an empty/placeholder repo, the
  instructions can't succeed and the error looks like an auth problem.

---

## How we resolved it

Precisely, in order:

1. **Error A (credentials) — attach the integration to the stack.** Attached an
   AWS cloud integration to the sandbox stack, retried the run: it then
   authenticated and planned, resolving `data.aws_caller_identity.current` to
   account `193456333226` and outputting `aws_account_id = "193456333226"`.
   *(This is exactly the fix prescribed in
   [troubleshooting-aws-credentials.md](troubleshooting-aws-credentials.md).)*

2. **Error B (malformed ARN) — correct the Role ARN.** Fixed the Viking
   integration's Role ARN to the valid form
   `arn:aws:iam::193456333226:role/spacelift-orbit-labs-role` and enabled tag
   session. Attach then validated cleanly — proving the trust policy had been
   correct all along; the `arn:` prefix was the only problem.

3. **Root cause 3 (two universes) — point the tutorial stack at the real repo.**
   Repointed `Prime Apollo 45` from the empty `dkontango/7777MP` to
   `dkontango/spacelift-gitops-demo` with project root `stacks/sandbox`, which
   already contains the tutorial's exact code (AWS provider `~> 6.0`,
   `aws_caller_identity`, `aws_account_id` output) and is verified end to end.

4. **Verification.** With the code and the attached, correctly-configured
   integration in the same place, a push triggers a run that initializes, plans,
   authenticates via keyless OIDC/AssumeRole, and reports the account id — the
   tutorial's success condition.

---

## The one-paragraph version (for the email)

> The prospect's `no valid credential sources` error almost always means the AWS
> cloud integration exists but isn't **attached to the specific stack** — attach
> it and re-run. A close cousin, `configure trust relationship`, frequently
> isn't a trust-policy problem at all but a **malformed Role ARN** (e.g. a
> missing `arn:` prefix) that fails Spacelift's live assume-role check. And in an
> AI-assisted setup, confirm the human and the agent are pointed at the **same
> stack and the same repository** — we hit the exact error above purely because
> one side's stack watched an empty placeholder repo while the working code lived
> in another. Pin the (stack, repo, project-root) tuple first; then the
> credential message tells you the truth.
