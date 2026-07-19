# Illustrated Walkthrough — Every Step, With Screenshots

A screenshot for each step of the whole GitOps workflow: AWS setup, the Spacelift
integration, creating a stack, deploying, and the OPA policy blocking a bad
change in a pull request.

> **Note on redaction.** Live screenshots have their AWS **account IDs** and
> **ARNs** blacked out (`████`). The AWS-console steps (2–4) are shown as
> faithful **labeled diagrams** rather than live console captures — the steps and
> exact values are accurate. Everything on the Spacelift side is a real,
> redacted screenshot from the account used to build this demo.

---

## The pipeline

![Architecture: Forgejo to GitHub to Spacelift to AWS](assets/steps/step-00-architecture.png)
*Push only to Forgejo → it mirrors to GitHub → Spacelift previews every PR → an OPA policy guards it → keyless OIDC deploys to AWS.*

## Step 1 — Where the tutorial lives

![Spacelift Stacks page with the Foundations guides panel](assets/steps/step-01-stacks-overview.png)
*After signing up (with GitHub), the in-app **Foundations** guides appear in the Assistant panel / LaunchPad. The **Stacks** page lists your stacks.*

## Step 2 — Register Spacelift as an OIDC provider (AWS)

![AWS IAM: add OpenID Connect identity provider](assets/steps/step-02-aws-oidc-provider.png)
*IAM → Identity providers → Add provider → OpenID Connect. Provider URL and audience are your Spacelift account URL. This is what makes AWS trust Spacelift's tokens — the basis of keyless auth.*

## Step 3 — Create the IAM role Spacelift assumes (AWS)

![AWS IAM: create role spacelift-orbit-labs-role](assets/steps/step-03-aws-create-role.png)
*Create `spacelift-orbit-labs-role` with a trust policy allowing `sts:AssumeRole` from Spacelift's principal (ExternalId `<account>@*`) plus a separate `sts:TagSession` statement. Copy the Role ARN — it must start with `arn:`.*

## Step 4 — Attach permissions to the role (AWS)

![AWS IAM: attach AmazonS3FullAccess and AmazonEC2FullAccess](assets/steps/step-04-aws-attach-policies.png)
*Attach `AmazonS3FullAccess` + `AmazonEC2FullAccess` (the tutorial's broad choice). For real accounts, a least-privilege scoped policy is safer.*

## Step 5 — Create the AWS cloud integration in Spacelift

![Spacelift: Set up AWS integration dialog](assets/steps/step-05-aws-integration-dialog.png)
*Integrations → AWS → Set up integration. Paste the **Role ARN**, leave **Assume role on worker = No**, set **Enable tag session = Yes**, region `us-east-1`. The trust-policy example is shown (principal account redacted).*

## Step 6 — The integration exists at the account level

![Spacelift: AWS integrations list](assets/steps/step-06-aws-integrations-list.png)
*The integration now appears in the account. **Important:** existing at the account level is not enough — it must be attached to each stack (Step 10).*

## Step 7 — Create a stack: details

![Spacelift: create stack — add stack details](assets/steps/step-07-create-stack-details.png)
*Stacks → Create stack. Name it and choose a space. (Spacelift also auto-generates opaque names like "Prime Apollo 45" elsewhere — track the full repo/role tuple, not just the name.)*

## Step 8 — Create a stack: connect source code

![Spacelift: create stack — connect to source code](assets/steps/step-08-create-stack-source.png)
*Pick GitHub → your repository → set the **Project root** (e.g. `stacks/sandbox`) and branch `main`. Because Forgejo mirrors to GitHub, this is the repo Spacelift watches.*

## Step 9 — Create a stack: choose vendor

![Spacelift: create stack — choose vendor OpenTofu](assets/steps/step-09-create-stack-vendor.png)
*Choose **OpenTofu / Terraform** (workflow tool: OpenTofu), a recent version, with **Manage state** on. Create & continue.*

## Step 10 — Attach the integration TO the stack

![Spacelift: AWS integration attached to the stack](assets/steps/step-10-integration-attached-to-stack.png)
*Stack → Settings → Integrations → attach the AWS integration (Read + Write). This is the step people miss — `no valid credential sources` almost always means the integration isn't attached **to this stack**. (ARN redacted.)*

## Step 11 — The OPA policy (the bonus)

![Spacelift: plan-block-public-s3 policy body in Rego](assets/steps/step-11-policy-body.png)
*A **Plan policy** in Rego that denies any change disabling an S3 bucket's public-access-block. Policy-as-code: version-controlled, unit-tested, attached to the stack.*

## Step 12 — Attach the policy to the stack

![Spacelift: policy attached to the stack](assets/steps/step-12-policy-attached.png)
*The `plan-block-public-s3` Plan policy attached to the stack. It now runs on every proposed run (PR preview).*

## Step 13 — Deploy: a finished run

![Spacelift: run finished, apply complete, website endpoint output](assets/steps/step-13-deploy-finished.png)
*A confirmed run applies via OpenTofu and finishes. Here the `guide-site` stack deployed the guide itself to S3 — the guide is deployed by the pipeline it documents.*

## Step 14 — The guardrail in action: PR blocked

![GitHub PR: Spacelift check failing due to policy](assets/steps/step-14-pr-policy-fail.png)
*A PR that flips a bucket public. Spacelift previews it and the check **fails** on the policy-bearing stack (and passes on one without the policy) — visible right on the GitHub PR.*

## Step 15 — Why it failed: the policy denial

![Spacelift: run FAILED, denied by plan policy with message](assets/steps/step-15-policy-deny-detail.png)
*The run is FAILED with the policy's own message: "S3 public access is not allowed … Set make_public = false." Caught in the preview, before merge.*

## Step 16 — Fix it: the PR passes

![GitHub PR: checks pass after the fix](assets/steps/step-16-pr-pass-after-fix.png)
*Push the fix (keep the bucket private) → Spacelift re-previews → the check passes → merge deploys. The developer got specific, immediate feedback and corrected the change before it shipped.*

---

## What this proves

Branch → PR → **Spacelift preview** → **policy blocks a risky change** → fix →
approve/merge → **deploy** — the full GitOps loop with keyless credentials and a
policy-as-code guardrail, driven from an on-prem Forgejo repo mirrored to GitHub.
