# Setup Runbook

Reproducible steps to stand up the demo. Values in `<angle brackets>` are
environment-specific; the ones used for this build are noted inline.

## 0. Prerequisites

- An AWS account with admin access to run the one-time bootstrap.
  (This build: account `193456333226`.)
- A Spacelift account (free tier). Sign up at `spacelift.io/free-trial` with
  GitHub. (This build: `dkontango`, **US region** →
  `https://dkontango.app.us.spacelift.io`.)
- A GitHub repo Spacelift can watch (the PR flow lives here).
- OpenTofu ≥ 1.6 locally for the bootstrap.

## 1. One-time AWS OIDC bootstrap (keyless credentials)

Registers Spacelift as an OIDC provider and creates the IAM role Spacelift
assumes. Run **once** with admin AWS keys; nothing long-lived is stored after.

```bash
cd bootstrap
cp terraform.tfvars.example terraform.tfvars
# set spacelift_issuer_host, e.g. dkontango.app.us.spacelift.io

export AWS_ACCESS_KEY_ID=...        # admin key, used only for this apply
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1

tofu init
tofu apply
```

Outputs (this build):

- `oidc_provider_arn = arn:aws:iam::193456333226:oidc-provider/dkontango.app.us.spacelift.io`
- `role_arn          = arn:aws:iam::193456333226:role/spacelift-gitops-demo`

Keep `role_arn` — it goes into Spacelift in step 3.

## 2. Connect the VCS

**GitHub (drives the required flow).** In Spacelift → Source control → GitHub →
install the Spacelift GitHub App on the repo. This enables PR previews and
merge-triggered deploys.

**Forgejo via Raw Git (capability contrast, optional).** Source control → Raw
Git → point at the Forgejo repo URL. Note this is one-way (manual sync/trigger,
no PR previews) — it exists in the demo to contrast with GitHub, not to drive
the flow.

## 3. AWS Cloud Integration (OIDC)

Spacelift → Cloud integrations → AWS → Add:

- **Role ARN:** the `role_arn` from step 1.
- Enable OIDC.

Do **not** add static AWS keys anywhere. (See
[troubleshooting-aws-credentials.md](troubleshooting-aws-credentials.md) for why
OIDC is the recommended path.)

## 4. Create the stacks

Create two stacks from the GitHub repo:

| Stack | Project root | Branch | Vendor | Labels |
|-------|--------------|--------|--------|--------|
| `spacelift-gitops-demo-dev`  | `stacks/dev`  | `main` | OpenTofu | — |
| `spacelift-gitops-demo-prod` | `stacks/prod` | `main` | OpenTofu | `production` |

For each stack:

- Set the IaC vendor to **OpenTofu** (pick a recent version).
- **Attach the AWS Cloud Integration** from step 3. *(Attaching is required — a
  created-but-unattached integration is the #1 cause of the "no valid credential
  sources" error.)*

The `production` label on the prod stack is what the Approval policy keys on.

## 5. Attach the policies

Spacelift → Policies → create one policy per file in [`policies/`](../policies),
paste the Rego, then attach to the stacks:

| Policy file | Type | Attach to |
|-------------|------|-----------|
| `plan-block-public-s3.rego` | Plan | both stacks |
| `approval-require-prod.rego` | Approval | both stacks (only acts on `production`) |
| `push-path-based.rego` | Push | both stacks |

Use Spacelift's **policy simulator** to sanity-check before attaching.

## 6. (Optional) Spacelift MCP for tooling

The hosted MCP server is at `https://dkontango.app.us.spacelift.io/mcp`
(browser-OAuth). To let a local assistant query the account, add to
`~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "spacelift": { "type": "http", "url": "https://dkontango.app.us.spacelift.io/mcp" }
  }
}
```

## 7. Drift detection + stack dependencies (paid — narrated only)

On the free tier these are unavailable. The dev/prod code supports the
dependency model, and drift detection would be enabled per-stack on Starter+.
In the demo these are shown as the next-tier value, not applied live.

## Security follow-ups for this build

- **Rotate** the AWS root password and the `masteruser` console password (both
  were exposed during setup). Enable MFA on root.
- The `masteruser` programmatic key lives in Bao
  (`kontango/secret/apps/spacelift-demo/aws`); it was only needed for the
  one-time bootstrap and can be rotated/disabled now that OIDC is in place.
