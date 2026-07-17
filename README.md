# Spacelift GitOps Demo

A demonstration of the **GitOps workflow with Spacelift**, built for a Solutions
Engineer take-home. It provisions AWS S3 buckets with **OpenTofu**, driven
through a full pull-request → preview → merge → deploy loop, with **OPA
policies** as guardrails and **keyless OIDC** for AWS credentials.

## The GitOps workflow shown

1. Branch off the default branch (`main`).
2. Open a Pull Request on GitHub.
3. **Spacelift previews** the plan on the PR (proposed run + PR status check).
4. Approve and merge the PR.
5. **Spacelift previews and deploys** the change on merge to `main`.

> **How this was built.** This environment was set up by directing an AI coding
> agent through the whole process — accounts, IaC, policies, and clicking
> through the AWS and Spacelift consoles. It simulates onboarding to Spacelift
> as an engineer with an AI agent, and the real blockers we hit are written up
> honestly in [`docs/build-journey.md`](docs/build-journey.md).

Plus, beyond the ask:

- **Policies (OPA):** a Plan policy that **blocks public S3 buckets** in the PR
  preview, an Approval policy that **gates production** behind a manual approval,
  and a path-based Push policy that routes each push to the right stack.
- **Keyless credentials:** AWS access via a Spacelift **AWS Cloud Integration
  with OIDC** — no static keys stored in Spacelift, a Context, or anywhere else.
- **VCS capability contrast:** the same OpenTofu code is also connected via
  Spacelift's **Raw Git** integration against a self-hosted **Forgejo** repo, to
  show — honestly — that Raw Git is *one-way* (manual sync/trigger, no PR
  previews or merge-deploy), and that the full PR-driven GitOps loop needs a
  first-class VCS integration like GitHub.

## Architecture

```
 Forgejo (git.konoss.org)          GitHub (public mirror)
  canonical / on-prem  ── mirror ──►  Spacelift VCS surface
                                          │  GitHub App: PR + merge webhooks
                                          ▼
                                      Spacelift  (OpenTofu, OPA policies)
                                          │  OIDC: AssumeRoleWithWebIdentity
                                          ▼
                                      AWS  (STS → temporary creds → S3 buckets)
```

- **Forgejo** is the canonical repo. It also appears as a **Raw Git** stack in
  Spacelift for the capability contrast above.
- **GitHub** is where the **PR lifecycle** happens (that is where Spacelift's PR
  previews and merge-deploys fire).
- **Spacelift** runs OpenTofu and evaluates the OPA policies.
- **AWS** hands back short-lived credentials via OIDC — nothing long-lived is
  stored.

## Repository layout

| Path | What it is |
|------|------------|
| [`modules/s3-bucket/`](modules/s3-bucket) | Reusable S3 bucket module. `public` toggles the public-access block — the lever the Plan policy inspects. |
| [`stacks/sandbox/`](stacks/sandbox) | **Approval-free** stack using credential-less providers (`random`/`null`) — the full GitOps + policy workflow with **no cloud integration, no IAM, no approvals**. The recommended first-run path. |
| [`stacks/dev/`](stacks/dev), [`stacks/prod/`](stacks/prod) | The real-cloud dev and prod environments (each a Spacelift stack, AWS via OIDC/AssumeRole). |
| [`policies/`](policies) | The three OPA policies + a passing unit test for the Plan policy. |
| [`bootstrap/`](bootstrap) | One-time OpenTofu that registers the Spacelift OIDC provider + IAM role in AWS. Run once with admin keys; Spacelift is keyless thereafter. |
| [`docs/troubleshooting-aws-credentials.md`](docs/troubleshooting-aws-credentials.md) | **Deliverable:** how to fix `no valid credential sources for Terraform AWS Provider`. |
| [`docs/recording-script.md`](docs/recording-script.md) | Scene-by-scene script for the demo video. |
| [`docs/spacelift-setup.md`](docs/spacelift-setup.md) | Reproducible setup runbook (account, stacks, OIDC, policies). |
| [`docs/build-journey.md`](docs/build-journey.md) | **Honest build log** — how this was set up (AI-agent-driven), the real blockers hit, and the SE takeaways. |

## Guardrails at a glance

| Policy | Type | Effect |
|--------|------|--------|
| [`plan-block-public-s3.rego`](policies/plan-block-public-s3.rego) | Plan | **Denies** any plan that makes an S3 bucket public; warns on bucket deletion. |
| [`approval-require-prod.rego`](policies/approval-require-prod.rego) | Approval | Auto-approves non-prod; **requires a manual approval** for stacks labeled `production`. |
| [`push-path-based.rego`](policies/push-path-based.rego) | Push | Routes pushes: feature branch → propose, default branch → track, unrelated paths → ignore. |

Validate the policies locally:

```bash
opa test policies/ --v1-compatible
```

## Notes on the free tier

Everything above runs on the Spacelift **free tier** (unlimited OPA policies,
AWS OIDC, unlimited runs). **Drift detection** and **stack dependencies** are
paid (Starter+); the dev/prod code and the drift story ship here and are
demonstrated as the next-tier value in the video, not applied live.

See [`docs/spacelift-setup.md`](docs/spacelift-setup.md) to reproduce the
environment.
