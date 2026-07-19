# Narration script — `workflow.mp4` (17-step walkthrough)

A ~68-second screen recording of the whole GitOps workflow, driven **live**
through the real AWS console, Spacelift, and GitHub, with a tracked yellow-halo
cursor. Steps captured live from the consoles are marked ● ; steps rendered from
the polished, already-redacted walkthrough asset (with the same animated cursor)
are marked ○. Every AWS **account ID** and **ARN** on screen is blacked out.

Read one block per on-screen step; each step holds ~2–4 seconds. Rebuild the
movie any time with `python3 docs/recording/build/make_video.py`.

---

**00 · The pipeline** ○
"Here's the whole loop. I push only to Forgejo — our on-prem canonical git. A
push-mirror propagates it to GitHub, where Spacelift previews every pull request.
An OPA policy guards the change, and AWS hands back short-lived credentials over
OIDC — nothing long-lived is stored anywhere."

**01 · Where the tutorial lives** ●
"This is Spacelift's Stacks page. You sign up with GitHub; the in-app Foundations
guides walk you through your first stack."

**02 · Register Spacelift as an OIDC provider (AWS)** ●
"On the AWS side, first I add Spacelift as an OpenID Connect identity provider.
This is what makes AWS trust Spacelift's tokens — the basis of keyless auth. This
is the live IAM console; the account ID up top is redacted."

**03 · Create the IAM role Spacelift assumes (AWS)** ●
"Then the role Spacelift assumes — `spacelift-orbit-labs-role`. Its trust policy
allows `sts:AssumeRole` from Spacelift's principal, plus a separate `TagSession`
statement. The role ARN and account IDs are blacked out."

**04 · Attach permissions (AWS)** ●
"I attach `AmazonS3FullAccess` and `AmazonEC2FullAccess` — the tutorial's broad
choice. In production you'd scope this down."

**05 · Create the AWS cloud integration in Spacelift** ○
"Back in Spacelift, I paste that role ARN into a new AWS cloud integration,
enable tag sessions, and set the region. No keys — just the role."

**06 · The integration exists at the account level** ●
"The integration now lives at the account level. Important: existing here is not
enough — it has to be attached to each stack, which is the step people miss."

**07 · The sandbox stack** ●
"Here's the sandbox stack, watching `stacks/sandbox` on `main`. You can see its
real run history — finished runs, and one failed run where I reproduced the
credential error on purpose."

**08 · Create a stack: connect source** ○
"When you create a stack you point it at your GitHub repo and set the project
root. Because Forgejo mirrors to GitHub, this is the repo Spacelift watches."

**09 · Create a stack: choose OpenTofu** ○
"Pick OpenTofu as the workflow tool, a recent version, with state managed by
Spacelift."

**10 · Attach the integration TO the stack** ○
"This is the fix for `no valid credential sources` — attach the AWS integration
to *this* stack, read + write. Account-level isn't enough."

**11 · The OPA Plan policy** ●
"The guardrail: a Rego Plan policy, `plan-block-public-s3`. It denies any change
that turns off an S3 bucket's public-access block."

**12 · Attach the policy to the stack** ○
"Attach it, and now it runs on every proposed run — every PR preview."

**13 · Deploy: a finished run** ○
"A confirmed run applies via OpenTofu and finishes — here it actually created a
real S3 bucket in AWS through the keyless integration."

**14 · The guardrail in action: PR blocked** ●
"Now the payoff. I open a PR that flips a bucket public. Spacelift previews it and
the check goes red — right on the GitHub PR. The stack *with* the policy fails;
the one without it passes."

**15 · Why it failed: the policy denial** ●
"On the Spacelift run: FAILED, 'denied by plan policy', 'Plan policies evaluated
to DENY', with the policy's own message — 'S3 public access is not allowed … Set
make_public = false.' Caught in the preview, before merge."

**16 · Fix it: the PR passes** ●
"I push the fix — keep the bucket private — Spacelift re-previews, the check goes
green, and merging deploys. The developer got specific, immediate feedback and
corrected the change before it shipped."

---

**Close.**
"That's the full GitOps loop: branch → PR → Spacelift preview → an OPA policy
blocks a risky change → fix → merge → deploy — keyless the whole way, driven from
an on-prem Forgejo repo mirrored to GitHub. Every AWS and Spacelift screen here
is live and real, just with the account identifiers redacted."

---

## How this movie is built

`build/make_video.py` assembles it: live Playwright cursor-tour frames
(`frames17/`) for the ● steps, plus synthesized cursor-pan clips over the
redacted walkthrough assets (`site/assets/steps/`) for the ○ steps. All frames
are letterboxed to 1280×720 on the guide's dark theme, a per-step title bar is
burned in, and ffmpeg stitches at 25 fps. The yellow-halo cursor + PII redaction
harness lives in `build/cursor-harness.js` / `build/capture-step.js`.

```bash
python3 docs/recording/build/make_video.py   # → docs/recording/workflow.mp4
```
