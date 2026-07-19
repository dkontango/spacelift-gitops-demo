# Spacelift Onboarding — By Hand (No AI)

A full click-by-click walkthrough of the Spacelift GitOps workflow, done
entirely by a human. Follow it top to bottom. It uses the **exact names**
Spacelift generates and its tutorials expect.

> **Read the two callouts first — they cause the most confusion:**
>
> ### ⚠️ Session management — one Spacelift session at a time
> Spacelift allows **only one active session per user**. The login UI even shows
> a **"Multi-session disabled"** control. Logging in via the CLI (`spacectl`,
> `terraform login`) invalidates your **web** session and vice-versa. If you
> later let an AI agent drive via a separate browser, **it will log you out** —
> only one session can be active. Plan for that: pick one driver at a time.
>
> ### ⚠️ Naming — the names are opaque and specific
> Spacelift **auto-generates** stack and integration names like **`Prime Apollo
> 45`** and **`Viking Terminal AWS`**. These names tell you nothing about which
> repo or IAM role they use. Always track the full tuple: **(stack, repository,
> project root, IAM role ARN, integration name)**. The tutorial's code uses
> exact literals — `random_pet`, `aws_s3_bucket.orbit_storage`,
> `bucket_prefix = "orbit-storage-"`, role `spacelift-orbit-labs-role` — match
> them exactly.

---

## Prerequisites

- A GitHub account (Spacelift signs up via OAuth — GitHub/GitLab/Google/MS).
- A GitHub repo Spacelift can watch, containing the starter Terraform/OpenTofu
  (a `random_pet` resource in a `main.tf`). This repo (`stacks/sandbox`) has it.
- An AWS account where you can create an IAM OIDC provider + role.

---

## Step 1 — Create your Spacelift account

1. Go to **https://spacelift.io/free-trial**.
2. Choose your **data region** (US or Europe). This sets your account hostname
   (`<account>.app.us.spacelift.io` for US) and, later, the AWS principal to
   trust. Pick **United States** for a US-based eval.
3. Click **GitHub** to sign up. Authorize the app. (Signing up with GitHub also
   auto-creates a built-in GitHub VCS integration — no separate App install.)
4. You land on **LaunchPad**. Note your account name in the URL
   (`https://<account>.app.us.spacelift.io`).

## Step 2 — Find the tutorial

The in-app tutorials are the **Foundations** guides. Open the **Assistant panel**
(right side of a stack page) or **LaunchPad → Learn**. You'll complete:
- **Credentials, Not Secrets — AWS Integration** (8 steps)
- **First Launch — Deploy Real Infrastructure** (7 steps)
- (Optional) **Guardrails — Enforce Policy Rules**

Each step has **Next step / Previous step / Complete** and a progress bar
("3/7"). Steps often gate on "a new run was triggered on your stack."

## Step 3 — Prepare AWS (one-time): OIDC provider + IAM role

The tutorial (guide "Credentials, Not Secrets") walks you through this in the AWS
console; the exact end-state is:

1. **IAM → Identity providers → Add provider → OpenID Connect.**
   - Provider URL: `https://<account>.app.us.spacelift.io`
   - Audience: the same URL. Click **Get thumbprint**.
2. **IAM → Roles → Create role**, trusted entity = the OIDC provider (or another
   AWS account for AssumeRole). Name it **`spacelift-orbit-labs-role`**.
3. **Attach permissions:** the tutorial says attach **AmazonS3FullAccess** +
   **AmazonEC2FullAccess** (broad, simple). Add description *"Role for Spacelift
   to manage AWS infrastructure."* Click **Create role**.
4. Open the role → copy its **Role ARN**
   (`arn:aws:iam::<ACCOUNT_ID>:role/spacelift-orbit-labs-role`). **It must start
   with `arn:`.**

**Trust policy** the role needs (us.spacelift.io principal shown):
```json
{ "Version": "2012-10-17", "Statement": [
  { "Effect": "Allow", "Action": "sts:AssumeRole",
    "Principal": { "AWS": "577638371743" },
    "Condition": { "StringLike": { "sts:ExternalId": "<account-name>@*" } } },
  { "Effect": "Allow", "Action": "sts:TagSession",
    "Principal": { "AWS": "577638371743" } } ]}
```
(EU/spacelift.io principal is `324880187172`. Keep the `TagSession` as its own
statement.)

## Step 4 — Create the AWS cloud integration in Spacelift

1. **Integrations → AWS → Set up integration** (or **Cloud integrations**).
2. **Name** it (this is an *account-level* integration — Spacelift may propose a
   name like *Viking Terminal AWS*; you can rename it).
3. **Role ARN:** paste the role ARN from Step 3. **Verify it starts with `arn:`.**
4. **Assume role on worker:** *No*. **Enable tag session:** *Yes*.
   **Duration:** 1h. **Region:** `us-east-1`.
5. Click **Set up**.

> If you get **"unauthorized: you need to configure trust relationship section in
> your AWS account"**: (a) check the Role ARN starts with `arn:` (a missing
> prefix is the usual culprit, *not* the trust policy); (b) IAM changes are
> eventually consistent — wait ~60 seconds and retry the save. Don't rewrite a
> correct trust policy chasing a propagation lag.

## Step 5 — Create a stack

**Stacks → Create stack.** (Spacelift auto-names it — e.g. *Prime Apollo 45*.)

1. **Stack details:** name/labels.
2. **Connect to source code:** GitHub → pick your repo
   (`dkontango/spacelift-gitops-demo`) → **Project root:** `stacks/sandbox` →
   branch `main`.
3. **Choose vendor:** **OpenTofu / Terraform** (workflow tool: **OpenTofu**),
   recent version, **Manage state** on.
4. **Create & continue.**

## Step 6 — Attach the integration TO THIS STACK

This is the step most people miss. The account-level integration is not enough.

1. On the stack → **Settings → Integrations → Attach cloud integration.**
2. Select your AWS integration → **Read** + **Write** checked → **Attach.**

> The error **`no valid credential sources for Terraform AWS Provider`** almost
> always means the integration is not attached **to this specific stack**. Attach
> it here and re-run.

## Step 7 — Follow "Credentials, Not Secrets" to the end

The tutorial has you add the AWS provider + a caller-identity data source to
`main.tf`, alongside the existing `random_pet`:

```hcl
terraform {
  required_providers { aws = { source = "hashicorp/aws", version = "~> 6.0" } }
}
provider "aws" { region = "us-east-1" }
data "aws_caller_identity" "current" {}
output "aws_account_id" { value = data.aws_caller_identity.current.account_id }
```

**Commit and push.** The push auto-triggers a run. Watch it go **INITIALIZING →
PLANNING**; it should resolve `aws_account_id` to your AWS account id. Advance the
guide with **Next step** until it completes.

## Step 8 — "First Launch — Deploy Real Infrastructure"

1. **Add an S3 bucket** to `main.tf` (the tutorial's exact code):
   ```hcl
   resource "aws_s3_bucket" "orbit_storage" {
     bucket_prefix = "orbit-storage-"
     tags = { name = "Orbit Labs Storage", managedBy = "Spacelift",
              mission = "First Launch", project = "Orbit-labs" }
   }
   ```
2. **Verify autodeploy is OFF** (Settings → Behavior) — the default. Commit + push.
3. A new **TRACKED** run appears and stops at **UNCONFIRMED** (autodeploy off).
   Review the plan — it should **create 1 resource** (`aws_s3_bucket.orbit_storage`).
4. Click **Confirm.** Watch **APPLYING → FINISHED.** Your bucket now exists in AWS
   (name starts `orbit-storage-…`).
5. **Verify** on the stack's **Resources** tab (and optionally the AWS S3 console).
6. **Enable autodeploy** (Settings → Behavior → Autodeploy → Save).
7. **Test autodeploy:** add a tag (`environment = "demo"`) to the bucket, commit +
   push. The run now goes straight **PLANNING → APPLYING → FINISHED**, skipping
   UNCONFIRMED. Click **Complete** — the guide is done.

## Step 9 (bonus) — Policies (Guardrails)

1. **Policies → Create policy** → Type **Plan**, Space **root**, name
   `plan-block-public-s3`. Paste the Rego (see `policies/plan-block-public-s3.rego`).
   **Create policy.**
2. Stack → **Policies → Attach policy** → type **Plan** → select
   `plan-block-public-s3` → **Attach.**
3. **Demonstrate it:** open a PR that makes the bucket public (flip the
   public-access-block off). Spacelift previews the PR and the policy **DENIES**
   it — the PR check fails with your policy message. Push a fix (keep it private)
   and the check passes.

---

## The run-queue gotcha

Spacelift runs blocking (tracked) runs **one at a time** per stack. A run left at
**UNCONFIRMED** blocks new ones. **Confirm** or **Discard** it to release the
queue. (The Confirm/Discard buttons sit right next to each other — click
carefully.)

## Quick error map

| Error | Real cause | Fix |
|---|---|---|
| `no valid credential sources …` | integration not attached to this stack | Step 6 |
| `configure trust relationship …` | malformed Role ARN, or IAM propagation lag | check `arn:` prefix; wait 60s, retry |
| Tutorial "still errors" on push | stack points at wrong/empty repo | fix the stack's repo + project root |
| New run stuck QUEUED | a prior UNCONFIRMED run blocks the queue | Confirm/Discard the blocker |
