# Spacelift GitOps Demo — Design

**Date:** 2026-07-17
**Purpose:** Take-home assignment for a Spacelift Solutions Engineer interview.
Two graded deliverables: (1) a short video demonstrating the GitOps workflow
with Spacelift, and (2) written instructions to troubleshoot an AWS-credentials
error. This spec covers the repo, the demo, and both deliverables.

---

## 1. Objectives (from the assignment)

Act as a Spacelift Solutions Engineer and:

- **Demo the GitOps workflow**, explaining it and highlighting the value
  Spacelift brings. The assignment defines the GitOps workflow as exactly
  these five steps:
  1. Branch off the default branch.
  2. Open a Pull Request for that branch.
  3. Have Spacelift **preview** the changes for the PR.
  4. Approve the changes and **merge** the PR.
  5. Have Spacelift **preview and deploy** the changes for the merge into the
     default branch.
  - **Bonus:** include policies.
- **Provide written troubleshooting instructions** for the error:
  `configuring Terraform AWS Provider: no valid credential sources for
  Terraform AWS Provider found.`

Free Spacelift account required. Spacelift docs are the primary reference; no
Spacelift support contact allowed.

---

## 2. Design decisions (locked)

| Decision | Choice | Rationale |
|---|---|---|
| IaC tool | **OpenTofu** | First-class Spacelift vendor; strong ecosystem signal for a Spacelift SE role. `.tf` syntax identical to Terraform. |
| Cloud target | **AWS S3 buckets** | Free-tier friendly, fast apply, and the S3 public-access setting is the perfect hook for a Plan policy. Keeps the demo coherent with the AWS troubleshooting question. |
| AWS credentials | **Spacelift AWS Cloud Integration + OIDC dynamic credentials** | Keyless, short-lived STS creds via IAM role trust. No secret stored anywhere. This is the best-practice "right answer" that the troubleshooting question steers toward — demo and runbook reinforce each other. |
| VCS (canonical) | **Forgejo** (`git.konoss.org`) | On-prem source of truth. Honors org convention. |
| VCS (Spacelift-facing) | **GitHub** (public mirror) | Spacelift supports GitHub/GitLab/Bitbucket/Azure DevOps — **not** Forgejo. Spacelift's GitHub App watches the mirror. **PR lifecycle happens on GitHub** (that is where Spacelift's PR webhooks fire); Forgejo mirrors code/branches only. |
| Secrets (Bao) | **Talking point, not a live dependency** | Spacelift's cloud workers can't reach overlay-only Bao without exposing it (violates the no-public-ports rule). OIDC removes the need for a stored secret entirely — a *stronger* use of the Bao story than wiring it in. |
| Multi-env | **dev + prod stacks** (code shipped; stack-dependency auto-trigger is paid) | Two free stacks are allowed; the paid "stack dependency" output-passing/auto-trigger is narrated as upsell. |

### Free-tier constraints (verified 2026-07-17)

Spacelift free plan: **2 users, 1 public worker, ≤200 managed resources,
unlimited runs, unlimited OPA policies (Plan + Approval included), cloud
integrations (AWS OIDC) supported.**

Paywalled (Starter+, ~$20k/yr — the cheap Starter tier was discontinued):

- **Drift detection** — not on free.
- **Stack dependencies** (stacks triggering each other / passing outputs) — not
  reliably on free.

**Consequence:** the core 5-step flow, the policy bonus, and OIDC are all
demonstrated **live** on the free tier. Drift detection and cross-stack
promotion are **narrated as the next-tier upsell** (slide/screenshot), with the
supporting code shipped in the repo so the narration is backed by real config.
This tier-aware framing is itself an authentic Solutions-Engineer move.

---

## 3. Architecture

```
  Developer
     │  git push
     ▼
 ┌──────────────┐   push-mirror (branches)   ┌──────────────┐
 │   Forgejo    │ ─────────────────────────▶ │   GitHub     │
 │ git.konoss   │   (canonical / on-prem)    │  (public)    │
 └──────────────┘                            └──────┬───────┘
                                                    │ GitHub App
                                        PR events / webhooks
                                                    ▼
                                            ┌───────────────┐
                                            │   Spacelift   │
                                            │  (OpenTofu)   │
                                            │  policies     │
                                            └──────┬────────┘
                                    OIDC (AssumeRoleWithWebIdentity)
                                                    ▼
                                            ┌───────────────┐
                                            │   AWS (STS)   │
                                            │  S3 buckets   │
                                            └───────────────┘
```

- **Forgejo** originates the code (on-prem story), push-mirrors branches to
  GitHub.
- **GitHub** is where the **PR** lives; Spacelift's GitHub App fires previews on
  PR open/update and deploys on merge to the default branch.
- **Spacelift** runs OpenTofu, evaluates OPA policies, and authenticates to AWS
  via OIDC (no static keys).
- **AWS** returns short-lived STS credentials; OpenTofu provisions S3 buckets.

---

## 4. Repository structure

```
spacelift-gitops-demo/
├── README.md                       # architecture + assignment mapping
├── modules/
│   └── s3-bucket/
│       ├── main.tf                 # aws_s3_bucket + public-access-block + versioning
│       ├── variables.tf            # name, tags, public (bool), versioning (bool)
│       └── outputs.tf              # bucket id/arn
├── stacks/
│   ├── dev/
│   │   ├── main.tf                 # calls the module for dev buckets
│   │   ├── providers.tf            # aws provider + backend note
│   │   └── variables.tf
│   └── prod/
│       ├── main.tf                 # prod buckets (consumes a shared prefix output)
│       ├── providers.tf
│       └── variables.tf
├── policies/
│   ├── plan-block-public-s3.rego   # Plan policy: deny public buckets, warn otherwise
│   ├── approval-require-prod.rego  # Approval policy: require manual approval for prod
│   └── push-path-based.rego        # Push policy: which paths trigger which stack
├── docs/
│   ├── troubleshooting-aws-credentials.md   # WRITTEN DELIVERABLE #1
│   ├── recording-script.md                  # scene-by-scene narration + on-screen checklist
│   ├── spacelift-setup.md                   # step-by-step account/stack/OIDC setup runbook
│   └── superpowers/specs/2026-07-17-…-design.md   # this spec
└── .gitignore
```

Stacks are configured in Spacelift (project root = `stacks/dev` and
`stacks/prod`). Policies are attached in the Spacelift UI (or as config-as-code
later); the `.rego` files are the source of truth in the repo.

---

## 5. Components

### 5.1 OpenTofu `s3-bucket` module
Single-purpose reusable module. Inputs: `name`, `tags`, `public` (bool),
`versioning` (bool). Creates an `aws_s3_bucket`, an
`aws_s3_bucket_public_access_block` (all four blocks = `!public`), and an
`aws_s3_bucket_versioning`. Outputs bucket id/arn. The `public` input is the
lever the Plan policy inspects.

### 5.2 dev / prod stacks
- **dev**: instantiates one or two buckets with dev tags; `public = false`.
- **prod**: same module, prod tags; demonstrates the promotion target. In the
  paid tier this would consume a dev output via stack dependency — here it
  carries a local `name_prefix` and the dependency is narrated.

### 5.3 Policies (OPA / Rego)
1. **`plan-block-public-s3`** (Plan policy) — parses the OpenTofu plan;
   `deny` any resource change that sets an S3 bucket public
   (public-access-block disabled / public ACL); `warn` on other notable
   changes. Demonstrated live: a PR flipping `public = true` is blocked in the
   PR preview.
2. **`approval-require-prod`** (Approval policy) — requires a manual approval
   before an apply on the prod stack (and/or when a run touches prod). Provides
   the "approve the changes" governance beat on camera.
3. **`push-path-based`** (Push policy) — maps changed paths to the stack that
   should react (e.g. `stacks/dev/**` → dev), so a push doesn't needlessly
   trigger unrelated stacks. Included in repo; mentioned if time allows.

### 5.4 Credentials — AWS OIDC
Spacelift AWS Cloud Integration. On each run the worker presents a signed OIDC
token; an AWS IAM role trust policy allows
`sts:AssumeRoleWithWebIdentity` for Spacelift's issuer, scoped by
`aud`/`sub` conditions. AWS returns short-lived creds injected into the run. No
access keys in Spacelift, contexts, env vars, or Bao.

---

## 6. Demo flow (video)

**Live (free tier):**
1. **Intro / architecture** — the diagram above; value framing (Git as the
   single source of truth, policy-as-code guardrails, keyless creds).
2. **Branch** off `main`, make a change in `stacks/dev` (add a bucket or a tag).
3. **Open PR on GitHub** → **Spacelift previews** the plan on the PR (proposed
   run visible in the PR checks + Spacelift UI).
4. **Policy in action** — a change that would create a *public* bucket is
   **blocked by the Plan policy** in the PR preview (deny + message).
5. **Approve + merge** the PR → Spacelift runs a **tracked run** and **deploys**
   to dev. If targeting prod, the **Approval policy** requires a manual approval
   first — the governance beat.
6. **OIDC** — show the run authenticating to AWS with no static credentials
   (call out the cloud integration), and the S3 bucket appearing in AWS.

**Narrated upsell (slide/screenshot, code shipped in repo):**
7. **Drift detection** — what it does, why GitOps needs it (Starter+).
8. **Stack dependencies / dev→prod promotion** — platform-scale story
   (Starter+).

**Close** — recap the value: PR-native previews, policy-as-code guardrails,
keyless OIDC, and the promotion/drift story as you scale.

Recording: screen recorder + separate narration. `docs/recording-script.md`
provides scene-by-scene narration and an on-screen checklist, with clean cut
points so any slow run doesn't stall the take.

---

## 7. Deliverable #1 — Troubleshooting runbook

`docs/troubleshooting-aws-credentials.md`. Answers the exact error as a
professional, reusable runbook:

- **What the error means** — the AWS provider found no credentials in its
  resolution chain. Note: the message literally says "Terraform AWS Provider"
  even under OpenTofu, because it is the *provider's* own error string (OpenTofu
  uses the same provider) — so the guidance is identical.
- **Credential resolution order** the provider walks (env vars → shared config
  → assumed role / web identity → EC2/instance metadata).
- **Fixes in Spacelift**, best-practice first:
  1. **AWS Cloud Integration + OIDC dynamic credentials** (recommended) — setup,
     IAM role trust policy, attaching the integration to the stack, common
     misconfigs (wrong `aud`/`sub`, role not attached, integration not enabled
     on the stack).
  2. **Static keys via a Spacelift context / env vars** — when/why, and why it's
     the weaker option.
  3. **IAM role assumption** variants.
- **How to verify** the fix (a run that reaches `AssumeRole`/plan cleanly;
  checking the run's environment).

---

## 8. Deliverable #2 — Recording script + setup runbook

- `docs/recording-script.md` — the video script (scenes, narration, checklist,
  cut points).
- `docs/spacelift-setup.md` — turnkey setup: create the free account, create the
  GitHub mirror, install the Spacelift GitHub App, configure the AWS OIDC
  integration + IAM role, create the dev/prod stacks, attach the policies. So
  the environment is reproducible and the recording is rehearsable.

---

## 9. Build split

- **Built now (no external accounts):** repo scaffold, README, OpenTofu module +
  dev/prod stacks, all three Rego policies, troubleshooting runbook, recording
  script, setup runbook, this spec. Committed to a **local git repo**; pushed to
  Forgejo when the overlay/Forgejo is reachable.
- **Done by the user (needs accounts):** recover AWS creds; create the free
  Spacelift account; create + push the GitHub mirror; install the GitHub App;
  wire the AWS OIDC integration + IAM role; create the two stacks; attach
  policies; record the video. Each step is scripted in `docs/spacelift-setup.md`.

---

## 10. Out of scope / YAGNI

- No self-hosted Spacelift worker (free tier = 1 public worker; Proxmox target
  ruled out for reachability/reliability).
- No live drift reconcile or live stack-dependency apply (paid tier) — narrated
  only, code shipped.
- No Bao runtime integration (OIDC removes the need; overlay exposure avoided).
- No EC2/VPC (S3 only — free, fast, sufficient for the policy hook).
