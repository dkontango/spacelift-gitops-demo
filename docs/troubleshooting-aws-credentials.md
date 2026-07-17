# Troubleshooting: "no valid credential sources for Terraform AWS Provider found"

**Error seen during a deployment:**

```
configuring Terraform AWS Provider: no valid credential sources for Terraform
AWS Provider found.
```

This runbook explains what the error means and walks through every way to fix
it in Spacelift, best-practice first.

> **Note on the wording.** The message says *"Terraform AWS Provider"* even when
> your stack uses **OpenTofu**. That string comes from the AWS *provider* itself
> (`hashicorp/aws`), which both Terraform and OpenTofu use — so the message and
> the fixes are identical regardless of which tool your stack runs.

---

## 1. What the error actually means

The AWS provider could not find credentials. It is not a network, permissions,
or Terraform/OpenTofu bug — the run reached the point of configuring the AWS
provider, looked through its credential sources, and found **nothing** to
authenticate with.

The AWS provider resolves credentials in this order and uses the first source it
finds:

1. **Static keys** — `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
   (+ optional `AWS_SESSION_TOKEN`) in the environment, or provider block args.
2. **Shared config/credentials files** — `~/.aws/credentials`, `~/.aws/config`
   (honoring `AWS_PROFILE`).
3. **Assumed role / web identity** — `AWS_ROLE_ARN` + a web-identity token file
   (`AWS_WEB_IDENTITY_TOKEN_FILE`), i.e. OIDC federation.
4. **Instance/container metadata** — EC2 instance profile, ECS task role, etc.

A Spacelift run executes on a **worker**, in a **fresh container**, in the
**cloud** — it does not inherit your laptop's `~/.aws` or your shell's env vars.
So unless you have *explicitly* given the run one of the sources above, the
provider finds none and throws this error. **The fix is to attach a credential
source to the stack.** There are three ways, below.

---

## 2. Fix A — AWS Cloud Integration with OIDC (recommended)

This is the modern, keyless approach: **no long-lived AWS keys anywhere.** On
each run, Spacelift presents a short-lived OIDC token; AWS STS exchanges it for
temporary credentials via an IAM role's trust policy. This is what feeds source
#3 (web identity) in the resolution chain above.

Set it up once:

**Step 1 — Register Spacelift as an OIDC provider in AWS.**
IAM → Identity providers → Add provider → OpenID Connect.
- **Provider URL:** `https://<account>.app.spacelift.io`
  (US region: `https://<account>.app.us.spacelift.io`)
- **Audience:** the same URL.
- Click **Get thumbprint**.

**Step 2 — Create an IAM role Spacelift can assume.** Trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/<account>.app.spacelift.io"
    },
    "Action": ["sts:AssumeRoleWithWebIdentity", "sts:TagSession"],
    "Condition": {
      "StringEquals": {
        "<account>.app.spacelift.io:aud": "https://<account>.app.spacelift.io"
      },
      "StringLike": {
        "<account>.app.spacelift.io:sub": "space:*:stack:*:run_type:*:scope:*"
      }
    }
  }]
}
```

Attach a permissions policy scoped to what the stack manages (least privilege).

**Step 3 — Create the Cloud Integration in Spacelift.**
Settings → Cloud integrations → AWS → Add. Paste the **role ARN**. Enable OIDC.

**Step 4 — Attach the integration to the stack.**
Stack → Settings → Integrations → attach the AWS integration. (This is the step
most often missed: creating the integration is not enough — it must be
*attached* to each stack that needs it.)

Re-run. The provider now finds web-identity credentials (source #3) and
authenticates.

*In this repo, all of the above (provider + role + least-privilege policy) is
codified in [`bootstrap/`](../bootstrap) as OpenTofu — the role ARN it outputs
is what you paste in Step 3.*

---

## 3. Fix B — static access keys via environment variables / a Context

The quick, less secure option — supplies source #1. Use only when OIDC isn't
possible (it stores a long-lived secret).

- **Per stack:** Stack → Environment → add variables
  `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (mark them **secret**), and
  `AWS_DEFAULT_REGION`.
- **Shared across stacks:** create a **Context** with those variables and attach
  it to each stack (Settings → Contexts).

Re-run. Downsides: the keys are long-lived, must be rotated manually, and live
in Spacelift. Prefer Fix A.

---

## 4. Fix C — IAM role assumption from a base credential

If your organization issues a base set of keys/role that must then assume a
target role, set (via stack env or a Context):

```
AWS_ROLE_ARN=arn:aws:iam::<ACCOUNT_ID>:role/<target-role>
```

together with a base credential (static keys, or the OIDC integration from Fix
A as the base). The provider then performs the role assumption (source #3). This
is common for cross-account setups.

---

## 5. If credentials *are* configured but you still see the error

Work down this checklist:

- **Integration not attached to the stack.** Creating the AWS Cloud Integration
  is not enough — attach it to the stack (Fix A, Step 4). This is the #1 cause.
- **Wrong `aud`/`sub` in the trust policy.** The `aud` must equal your account
  URL; the `sub` `StringLike` must match the run
  (`space:<space>:stack:<stack>:run_type:<type>:scope:<read|write>`). A too-tight
  `sub` blocks `AssumeRoleWithWebIdentity`, surfacing as no valid credentials.
- **Secret env vars not marked secret / typo'd names.** They must be exactly
  `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.
- **Private worker without an instance profile.** If you run your own worker
  pool and rely on instance metadata (source #4), confirm the worker's
  EC2/ECS role actually exists and is attached.
- **Region missing.** Some provider/back-end configs fail early without
  `AWS_DEFAULT_REGION` or a `region` in the provider block.

---

## 6. How to verify the fix

1. Trigger a run and open its logs. The **Initializing** phase should configure
   the AWS provider **without** the credential error.
2. Add a one-off check to confirm *which* identity the run assumed — a
   `before_plan` hook or a quick task:
   ```
   aws sts get-caller-identity
   ```
   With OIDC you'll see the assumed-role ARN
   (`arn:aws:sts::<ACCOUNT_ID>:assumed-role/<role>/<session>`), proving the
   web-identity exchange worked and no static key was used.
3. The plan should now read live AWS state instead of failing at provider
   configuration.

**Bottom line:** the error means the run had no credential source. Give the
stack one — ideally the keyless **AWS Cloud Integration (OIDC)** — and make sure
it's **attached to the stack**.
