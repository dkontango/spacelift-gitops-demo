# One-time bootstrap: registers Spacelift as an OIDC identity provider in this
# AWS account and creates the IAM role Spacelift assumes via web-identity
# federation. Applied ONCE locally with admin AWS keys; after that, Spacelift
# authenticates with NO long-lived credentials — it presents a short-lived OIDC
# token and AWS STS returns temporary creds. This is the keyless pattern the
# demo showcases (and the "right answer" to the troubleshooting question).

locals {
  # Full issuer host, e.g. dkontango.app.us.spacelift.io (US region) or
  # <account>.app.spacelift.io (EU). Passed in directly to avoid guessing the
  # regional suffix.
  spacelift_issuer_host = var.spacelift_issuer_host
  spacelift_issuer_url  = "https://${local.spacelift_issuer_host}"
}

# Spacelift as an OIDC provider. The audience (client ID) equals the issuer
# hostname — Spacelift mints tokens with aud = the account's Spacelift URL.
resource "aws_iam_openid_connect_provider" "spacelift" {
  url             = local.spacelift_issuer_url
  client_id_list  = [local.spacelift_issuer_url]
  thumbprint_list = var.oidc_thumbprints
}

# Trust policy: allow Spacelift's OIDC provider to assume this role, but ONLY
# for tokens whose aud matches our account and whose sub matches our stacks.
# sub format: space:<space>:stack:<stack>:run_type:<type>:scope:<read|write>
data "aws_iam_policy_document" "trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity", "sts:TagSession"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.spacelift.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.spacelift_issuer_host}:aud"
      values   = [local.spacelift_issuer_url]
    }

    # Restrict to this account's stacks. Tighten to specific stack IDs once they
    # exist (e.g. space:*:stack:spacelift-gitops-demo-*:run_type:*:scope:*).
    condition {
      test     = "StringLike"
      variable = "${local.spacelift_issuer_host}:sub"
      values   = [var.allowed_sub]
    }
  }
}

resource "aws_iam_role" "spacelift" {
  name                 = var.role_name
  assume_role_policy   = data.aws_iam_policy_document.trust.json
  max_session_duration = 3600

  tags = {
    Project   = "spacelift-gitops-demo"
    ManagedBy = "opentofu-bootstrap"
    Purpose   = "spacelift-oidc-assumed-role"
  }
}

# Demo-scoped permissions: S3 only. NOT AdministratorAccess — least privilege
# is part of the story. Scoped to buckets this demo creates by name prefix.
data "aws_iam_policy_document" "permissions" {
  statement {
    sid       = "S3BucketLifecycle"
    effect    = "Allow"
    actions   = ["s3:*"]
    resources = [
      "arn:aws:s3:::${var.bucket_prefix}-*",
      "arn:aws:s3:::${var.bucket_prefix}-*/*",
    ]
  }

  # Bucket create/list operations that require account-level (list buckets)
  # scope. ListAllMyBuckets cannot be resource-scoped.
  statement {
    sid       = "S3List"
    effect    = "Allow"
    actions   = ["s3:ListAllMyBuckets", "s3:GetBucketLocation"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "spacelift" {
  name   = "${var.role_name}-s3"
  role   = aws_iam_role.spacelift.id
  policy = data.aws_iam_policy_document.permissions.json
}
