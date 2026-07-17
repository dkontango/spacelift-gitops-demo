# Build Journey — Onboarding to Spacelift with an AI Agent

**Honest framing.** This environment was built by driving an AI coding agent
(Claude) through the entire setup — creating accounts, writing the IaC and
policies, and clicking through the Spacelift and AWS consoles via browser
automation. I directed the process and made the decisions; the agent executed.

I did it this way deliberately. It simulates what onboarding to Spacelift looks
like for a modern engineer who has an AI agent at hand — which is increasingly
how people evaluate new platforms. The friction we hit is real onboarding
friction, and surfacing it is exactly the kind of feedback a Solutions Engineer
should bring back. Nothing below is polished after the fact to hide a wrong
turn; the wrong turns are the point.

---

## What we set out to build

- The Spacelift GitOps loop (branch → PR → preview → merge → deploy) with
  **OpenTofu** against **AWS S3**.
- **OPA policies** as guardrails (block public buckets; gate prod with an
  approval).
- **Keyless AWS credentials** (no static keys stored anywhere).
- Canonical repo on self-hosted **Forgejo**, mirrored to **GitHub** (the VCS
  Spacelift actually drives), plus a **Forgejo-via-Raw-Git** stack as an honest
  capability contrast.

## What we ended up with

- Forgejo repo (canonical) + private GitHub mirror.
- AWS OIDC/AssumeRole bootstrap applied as OpenTofu (`bootstrap/`).
- Spacelift account (`dkontango`, US region), AWS cloud integration, an
  OpenTofu `dev` stack.
- **Verified end to end:** a triggered run assumed the AWS role with no static
  keys, planned `3 to add`, applied, and created a real S3 bucket
  (`spacelift-gitops-demo-dev-app-kontango`).

---

## The path, step by step — including every blocker

### 1. Repo and IaC (smooth)
Created the canonical repo on Forgejo, wrote the OpenTofu module + dev/prod
stacks and the three OPA policies. The policies are unit-tested locally with
`opa test` (the plan policy provably denies a public bucket). No blockers here.

**Snag (minor, self-inflicted):** the workstation's `~/.gitconfig` rewrites
`git.konoss.org` → an internal overlay hostname that wasn't reachable, so
`git push` to Forgejo failed until we pushed with an inline-credential URL that
dodged the rewrite. Not a Spacelift issue — local config.

### 2. AWS credentials (the first real friction)
The intent was keyless OIDC, but to *bootstrap* OIDC you need admin AWS access
once. Here we hit a sequence of credential-type confusions that are worth
naming, because a new user absolutely will hit them:

- We were first handed an **AWS console login** (email + password) and treated
  it as if it were API keys. It isn't — a console password can't drive the CLI
  or OpenTofu. Recognizing "console credential ≠ programmatic credential" is a
  non-obvious step.
- The IAM user we logged in as (`masteruser`) had **no permissions at all** —
  it couldn't even create its own access key. Resolving this required signing
  in as the **AWS root user** (which triggered **email-based MFA**), attaching
  `AdministratorAccess`, and only then minting a programmatic key.
- Once we had a real `AKIA...` key, we stored it in our secrets manager
  (OpenBao) and verified it with `aws sts get-caller-identity`.

**SE takeaway:** the single biggest onboarding barrier here was *AWS-side
identity setup*, not Spacelift. A guided "here's precisely the IAM user + policy
you need, and here's how to get a key" would remove a lot of first-run pain.

### 3. The OIDC bootstrap (clean, once creds existed)
We wrote the Spacelift OIDC provider + IAM role as OpenTofu and applied it in
one shot. `tofu plan` → `3 to add` → apply. This part was exactly as smooth as
Spacelift's docs suggest.

### 4. Creating the Spacelift account (smooth, with one gotcha)
Signup is **OAuth-based** (GitHub/GitLab/Google/Microsoft) — there's no
email/password path, which surprised us at first. We signed up with GitHub.

**Nice payoff:** because we signed up via GitHub, Spacelift auto-created a
**built-in GitHub VCS integration** — no separate GitHub App install dance. That
was a genuinely smooth moment.

One real decision: the signup offers a **data region** (defaulted to Europe). We
switched to US. This matters more than it looks — it changes the account
hostname *and* the AWS principal used in the trust policy (below).

### 5. The AWS cloud integration + trust policy (the hard blocker)
This is where we lost the most time, and it's the most useful feedback.

We created the AWS integration in Spacelift (pasted the role ARN, left "assume
role on worker" off for the public worker, enabled tag session) and attached it
to the stack. Attaching **failed**:

> `unauthorized: you need to configure trust relationship section in your AWS account`

Then, after we thought we'd fixed it, the first run **failed** at job
assignment:

> `job assignment failed: IAM role access denied`

Two distinct trust-policy mistakes, each non-obvious:

1. **Wrong assumption about the auth method.** We initially wrote the role's
   trust for OIDC `AssumeRoleWithWebIdentity` only. But Spacelift's **public
   shared worker** assumes the role via plain `sts:AssumeRole` from Spacelift's
   own AWS account, scoped by an **ExternalId** (`<account>@*`). The role has to
   trust *that*. (The account differs by region — `577638371743` for
   us.spacelift.io, `324880187172` for spacelift.io.)

2. **`sts:TagSession` must be its own statement.** With tag-session enabled,
   combining `sts:TagSession` into the same statement as `sts:AssumeRole` (which
   carried the ExternalId condition) caused AWS to deny the assume. Splitting
   `TagSession` into a separate statement with no ExternalId condition fixed it.

We diagnosed this by reading the exact error, comparing Spacelift's documented
trust policy against what we'd written, and correcting the OpenTofu. After the
fix, the run sailed through.

**SE takeaway:** the trust-policy step is the sharpest edge in the whole
onboarding. The in-console example is close but easy to misread, the failure
messages ("access denied", "configure trust relationship") don't point at
*which* statement is wrong, and the region-specific principal + the
separate-TagSession-statement requirement are both easy to miss. This is the
first thing I'd want to smooth for a prospect — ideally a copy-pasteable,
region-aware, tag-session-correct trust policy generated right in the
integration screen.

### 6. End-to-end verification (success)
With the trust policy correct:

- Triggered a run → **Initializing → Planning** (it assumed the role — the
  credential problem was gone) → **`Plan: 3 to add`**.
- Confirmed → **Apply** → the S3 bucket appeared in AWS.

We watched the bucket show up with `aws s3api list-buckets`. Keyless,
policy-ready, real infrastructure.

---

## The realization: most of that friction was self-inflicted

After getting the AWS path working, we stepped back and asked the question a
real prospect would ask: **in my org, "create an IAM user / attach admin /
mint a key / add a trust relationship" is a change-request that needs security
approval. Do I really have to do all that just to evaluate Spacelift?**

The answer is **no** — and we'd taken the hard road unnecessarily.

Spacelift lets a stack run with **no cloud integration attached at all**. If the
OpenTofu uses **credential-less providers** (`random`, `null`, `local`, `tls`,
`time`), a run needs zero cloud credentials, zero IAM, and zero approvals — and
you still get the *entire* Spacelift experience: managed state, PR previews,
plan diffs, OPA policies, approvals, the full GitOps loop.

We built exactly this as [`stacks/sandbox`](../stacks/sandbox) — a `random_pet`
+ `null_resource` stack with a matching Plan policy
([`plan-sandbox-block-public.rego`](../policies/plan-sandbox-block-public.rego))
that blocks a "public" resource, mirroring the S3 scenario with no cloud. We
verified it end to end in Spacelift:

```
random_pet.name: Creation complete after 0s [id=stable-bull]
null_resource.app: Creation complete after 0s
Apply complete! Resources: 2 added, 0 changed, 0 destroyed.
```

No integration, no credentials, no approval. A brand-new user could see every
concept the evaluation cares about **in minutes**, then decide whether the
one-time, approval-gated cloud-trust setup is worth doing.

**This is the single most important SE takeaway of the whole exercise.** The
right first-run story is: *sandbox stack first (zero approvals, full value),
real cloud second (once you've done the one-time trust setup)*. We now lead the
demo that way. The IAM/trust friction is real and worth smoothing — but it
should never be the *first* thing a prospect hits, and it doesn't have to be.

## Where the AI flow diverged from Spacelift's tutorial (honest note)

Spacelift's own getting-started tutorial prescribes a **specific** IAM role
setup. Our AI-driven flow did **not** follow it — worth calling out plainly:

| Tutorial instruction | What the AI flow did |
|---|---|
| Attach managed policies **AmazonS3FullAccess** + **AmazonEC2FullAccess** | Wrote a **custom inline policy**, `s3:*` scoped to `spacelift-gitops-demo-*` buckets only — **no EC2**, no account-wide S3 |
| Name the role **`spacelift-orbit-labs-role`** | Named it **`spacelift-gitops-demo`** |
| Description: **"Role for Spacelift to manage AWS infrastructure"** | No matching description (tags only) |
| (Tutorial assumes the trust relationship is already set) | Built the trust policy from scratch in OpenTofu — and hit the trust-relationship blocker described above |

This divergence is itself an interesting SE observation. The tutorial trades
**security for simplicity** — `AmazonEC2FullAccess` + `AmazonS3FullAccess` are
broad, wide-open-on-two-services managed policies that minimize first-run
friction. The AI agent did the opposite: it reached for **least privilege**,
scoping the role to exactly the buckets this demo manages. Both "work," but they
represent opposite security postures, and the agent's instinct pushed *away*
from the prescribed tutorial toward a tighter policy.

Neither is simply "right" — the tutorial is optimizing for a fast, unblocked
first run; the least-privilege version is what you'd actually want in a real
account. For completeness and honesty, this repo now contains **both**: the
verified least-privilege role (`bootstrap/`, `spacelift-gitops-demo`) and the
tutorial-exact role (`bootstrap-tutorial-role/`, `spacelift-orbit-labs-role`
with the two managed policies and the prescribed description), so the divergence
is visible rather than hidden.

**SE takeaway:** an AI agent following "good practice" will quietly deviate from
a prescriptive tutorial. That's usually desirable, but it means tutorials and
guardrail-policies should either state the intended posture explicitly or expect
(and validate) tighter variations. It also means "did the user follow the
tutorial?" and "did the user end up secure?" can have different answers.

## Honest assessment of the experience

**What was genuinely smooth**
- OpenTofu as a first-class vendor — zero friction, picked it from a dropdown.
- GitHub signup auto-wiring the VCS integration.
- Spacelift-managed state — no backend to configure.
- The run UI (plan diff, confirm/discard, live logs) is clear and fast.

**What caused real friction (in order of pain)**
1. The AWS IAM **trust policy** (region principal + separate TagSession
   statement) — two failed runs before it worked.
2. AWS-side **identity bootstrap** (console-vs-programmatic creds, an
   unprivileged IAM user, root MFA) — not Spacelift's fault, but it's the first
   wall a new user hits, and Spacelift's success depends on getting past it.
3. Minor: OAuth-only signup and the region default were mild surprises.

**What I'd bring back as an SE**
- **Lead every evaluation with a no-cloud sandbox stack.** It's the fastest path
  to value and needs zero approvals — the IAM/trust work can wait until the
  prospect has already seen the workflow and wants real cloud. This should be
  the documented "first 10 minutes" story.
- The trust-policy step deserves a generated, copy-paste, region-aware snippet
  in the integration screen, with the tag-session statement already split out.
- Error messages at attach/assign time could name the failing condition.
- A short "AWS prerequisites" checklist (IAM user, minimal policy, how to mint a
  key) would de-risk the cloud step for prospects who don't live in AWS daily.

None of these are dealbreakers — we got a full keyless GitOps deploy working.
They're the difference between a good first-run and a frustrating one, which is
exactly what an SE is there to smooth.
