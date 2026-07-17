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

# Trust policy — allows Spacelift to assume this role two ways, both keyless
# (no static access keys are ever stored):
#
#   1. sts:AssumeRole + ExternalId (public shared workers). Spacelift's own AWS
#      account assumes the role, scoped by an ExternalId unique to this account
#      (<account>@<stack>...). This is the method the free-tier public worker
#      uses and what Spacelift validates on integration attach.
#   2. sts:AssumeRoleWithWebIdentity (OIDC, private workers / web identity).
#      Retained so the same role works if a private worker pool is added later.
data "aws_iam_policy_document" "trust" {
  # 1. Public-worker AssumeRole with ExternalId (the documented Spacelift
  #    pattern for us.spacelift.io). ExternalId is scoped to this account.
  statement {
    sid     = "SpaceliftAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = [var.spacelift_aws_account_id]
    }

    condition {
      test     = "StringLike"
      variable = "sts:ExternalId"
      values   = ["${var.spacelift_account_name}@*"]
    }
  }

  # 2. TagSession — required as its OWN statement (no ExternalId condition) so
  #    AWS allows the session tags Spacelift attaches during AssumeRole.
  statement {
    sid     = "SpaceliftTagSession"
    effect  = "Allow"
    actions = ["sts:TagSession"]

    principals {
      type        = "AWS"
      identifiers = [var.spacelift_aws_account_id]
    }
  }

  # 3. OIDC web identity (kept for a future private-worker / federated setup).
  statement {
    sid     = "SpaceliftWebIdentity"
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
