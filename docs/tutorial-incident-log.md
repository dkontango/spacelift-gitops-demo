# Tutorial Incident Log — Driving Spacelift's Foundations Guides with an AI Agent

A near-verbatim "recording" of what happened while an AI agent (Claude) drove
Spacelift's in-app **Foundations** tutorials end to end via browser automation,
under human direction. It captures the exact errors we produced, the inputs that
caused them, why each is a real-world pitfall, and how we resolved them.

The value of this document is that the failures were **not** Spacelift product
bugs. They were **coordination and naming failures** between a human and an AI
agent — which is exactly the class of problem that will dominate AI-assisted
onboarding, and exactly what a Solutions Engineer must be able to see and
explain.

**Scope of what was completed live:**
- Guide 1 — *Credentials, Not Secrets: AWS Integration* (8 steps): completed.
- Guide 2 — *First Launch: Deploy Real Infrastructure* (7 steps): completed —
  deployed a **real S3 bucket** (`orbit-storage-afb96b3b134b704fe3cf496220`),
  then verified **autodeploy** by pushing a tag change that applied with no
  manual confirmation.

---

## The environment that existed (and the trap inside it)

Two parallel sets of objects existed, with **auto-generated and
human/AI-chosen names that did not line up**:

| Concept | The human's tutorial objects | The AI agent's objects |
|---|---|---|
| Stack | **Prime Apollo 45** (Spacelift auto-named) | `spacelift-gitops-demo-sandbox` / `-dev` (agent-named) |
| Repo the stack watched | **`dkontango/7777MP`** (empty; only a README) | `dkontango/spacelift-gitops-demo` (all the real code) |
| AWS integration | **Viking Terminal AWS** (auto-named) | `aws-spacelift-gitops-demo`, `aws-orbit-labs-role` (agent-named) |
| IAM role | `spacelift-orbit-labs-role` (tutorial: S3+EC2 FullAccess) | `spacelift-gitops-demo` (agent: least-privilege S3-only) |

**Nothing shared a name, and the two sides were pointed at different repos.**
That single fact caused most of the errors below.

---

## Timeline of errors, causes, and fixes

### Incident 1 — `no valid credential sources` (the prospect's exact error)

**What we saw (Spacelift run log):**
```
Error: No valid credential sources found
  with provider["registry.opentofu.org/hashicorp/aws"], on providers.tf line 25
Error: failed to refresh cached credentials, no EC2 IMDS role found,
operation error ec2imds: GetMetadata, request canceled, context deadline exceeded
```

**Input to Claude that caused it:** the human said *"the AWS integration is
attached."* True — but for the **`-dev`** stack, not for the **sandbox** stack
the tutorial code was being pushed to. Claude took the statement at face value
and pushed the AWS-provider change; the sandbox stack had **no cloud integration
attached**, so the AWS provider found no credentials and timed out on IMDS.

**Why it's a pitfall:** "an integration exists in the account" ≠ "an integration
is attached to *this* stack." The error message blames credentials; the real
cause is a missing per-stack attachment. This is the single most common cause of
the prospect's error.

**Fix:** attach the AWS cloud integration to the specific stack, retry. The run
then authenticated and planned, resolving
`data.aws_caller_identity.current` → `193456333226`.

### Incident 2 — `configure trust relationship` (misleading trust error)

**What we saw (on integration attach):**
```
unauthorized: you need to configure trust relationship section in your AWS account
```

**Input/cause:** the **Viking Terminal AWS** integration was configured by hand
with a Role ARN of `aws:iam::193456333226:role/...` — **missing the leading
`arn:`**. Spacelift's attach-time validation does a live `sts:AssumeRole`; an
unresolvable ARN fails, and the UI reports it as a *trust relationship* problem
even though the role's trust policy was completely correct.

**Why it's a pitfall:** the message points at the trust policy — the one thing
that was fine. A prospect (or an agent) can burn an hour re-verifying a correct
trust policy. The real issue was a one-character paste error in the ARN.

**Fix:** correct the Role ARN to
`arn:aws:iam::193456333226:role/spacelift-orbit-labs-role` and enable tag
session. Validation then passed instantly — proving the trust policy had always
been right.

### Incident 3 — the tutorial stack watched an empty repo (root cause of "still erroring")

**What we saw:** the tutorial's "Next step" gate and pushes kept "returning an
error," yet the stack showed only an old FINISHED "Initial commit" run.

**Cause:** **Prime Apollo 45** (the human's tutorial stack) watched
**`dkontango/7777MP`**, a repo containing **only a `README.md`** — no `main.tf`,
no `random_pet`. Meanwhile every code change the agent made went to
**`dkontango/spacelift-gitops-demo`**, which that stack didn't watch. The
tutorial says *"edit main.tf alongside your existing random_pet resource"* — but
there was no `main.tf` and no `random_pet` in the repo the stack was pointed at.

**Why it's the key pitfall:** in AI-assisted work, the human and the agent can
each be **correct about a different environment**. Neither stated which
`(stack, repo, project-root)` was authoritative, so both were right about
different objects and nothing converged. The specific, auto-generated names
("Prime Apollo 45", "Viking Terminal AWS") made it worse — they carry no hint of
which repo/role they belong to, and the agent had invented its own parallel
names on top.

**Fix:** repoint **Prime Apollo 45**'s source to
`dkontango/spacelift-gitops-demo`, project root `stacks/sandbox` (which already
had the tutorial code). The very next run authenticated, planned, and output
`aws_account_id = "193456333226"` — and the tutorial's "Next step" advanced.

### Incident 4 — queued runs blocked by a stale UNCONFIRMED run

**What we saw:** a freshly pushed run sat at **QUEUED**, "Blocked by" an earlier
run stuck at UNCONFIRMED.

**Cause:** Spacelift serializes blocking (tracked) runs per stack. A previous run
left at UNCONFIRMED (because autodeploy was off) holds the queue until it is
Confirmed or Discarded. This is by design, not a bug.

**Pitfall / agent error:** while trying to Discard the blocker, the agent once
clicked **Confirm** instead (the two buttons sit adjacent and refs shifted
between reading and clicking). Harmless here — it applied idempotent sandbox
resources — but it's a real risk of UI automation: *adjacent
destructive/constructive actions + a shifting DOM.* Always re-locate the exact
control immediately before clicking.

**Fix:** Discard the stale UNCONFIRMED run to release the queue; the new run then
proceeded.

### Incident 5 — a lost commit from a diverged local `main`

**What we saw:** a committed doc (`troubleshooting-case-study.md`) reported as
pushed, but was absent from GitHub `main`.

**Cause:** the agent committed on a local `main` that had **diverged** from the
remote merge commit, so the doc lived only locally; a later `git reset --hard
github/main` then wiped it from the working tree.

**Pitfall:** "push succeeded" against a diverged branch does not mean the change
is on the branch you think. **Fix:** recovered the commit from reflog and
cherry-picked it back onto the correct `main`.

---

## The naming pitfall, stated plainly (this was the core of the objective)

- **Spacelift auto-generates memorable-but-opaque names** for stacks and
  integrations: *Prime Apollo 45*, *Viking Terminal AWS*. These names encode
  **nothing** about which repo, role, or environment they map to.
- **An AI agent will invent its own naming scheme** in parallel
  (`spacelift-gitops-demo-*`, `aws-orbit-labs-role`, `spacelift-gitops-demo`
  role). Left unreconciled, you end up with two naming universes for the same
  intent.
- **The tutorial's code uses specific literal names** (`random_pet`,
  `aws_s3_bucket.orbit_storage`, `bucket_prefix = "orbit-storage-"`,
  `spacelift-orbit-labs-role`). If the attached role is a least-privilege one
  scoped to a *different* prefix (the agent's `spacelift-gitops-demo-*`), the
  tutorial's `orbit-storage-*` bucket would be **denied** — a silent
  naming/permission mismatch. (Prime Apollo 45 used the FullAccess tutorial role,
  so it was permitted; had it used the agent's least-priv role, it would have
  failed with an access-denied on `s3:CreateBucket`.)

**Rule that would have prevented every incident above:** before running or
debugging anything, pin and agree the exact tuple —
**(stack name, repository, project root, IAM role, integration name)** — and
verify the integration is *attached to that stack*. The moment the human and the
agent share that tuple, the parallel-universe class of error disappears.

---

## What the completed tutorial actually proved (the happy path)

Once repointed and correctly wired, the full Foundations flow ran green:

1. **Credentials guide:** stack authenticated to AWS via keyless assume-role;
   `aws_caller_identity` returned account `193456333226`.
2. **First Launch guide, manual approval:** pushed an `aws_s3_bucket` change →
   tracked run stopped at **UNCONFIRMED** (autodeploy off) → reviewed plan
   (`3 to add`) → **Confirm** → APPLYING → **FINISHED**; real bucket
   `orbit-storage-afb96b3b134b704fe3cf496220` created in AWS.
3. **Autodeploy:** enabled autodeploy, pushed a tag change → run went straight
   **PLANNING → APPLYING → FINISHED**, skipping UNCONFIRMED
   (`Resources: 0 added, 1 changed, 0 destroyed`).

Both deployment modes demonstrated: **manual approval** (safer, slower) and
**autodeploy** (faster, requires trust) — the exact contrast the tutorial
teaches.

---

## SE takeaways (what to bring back)

1. **Per-stack attachment is the #1 credential gotcha.** The console should make
   "this stack has no cloud integration attached" impossible to miss when a run
   fails on credentials.
2. **The trust-relationship error is overloaded.** A malformed/again-unresolvable
   Role ARN reports as a trust-policy problem. Validate the ARN shape and name
   the actual failing check.
3. **Auto-generated names are a real hazard in AI-assisted flows.** Consider
   letting users name stacks/integrations during onboarding, or surfacing the
   `(repo, project root, role)` tuple prominently on the stack header, so a human
   and an agent can't silently diverge.
4. **The tutorial assumes the stack's repo already contains `random_pet`.** When
   the stack points at an empty/placeholder repo, the instructions can't succeed
   and the failure masquerades as an auth error. A first-step check ("does this
   stack's repo contain the starter code?") would catch it.
