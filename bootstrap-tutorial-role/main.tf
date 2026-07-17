# Tutorial-EXACT IAM role, built to follow Spacelift's getting-started
# instructions literally, alongside the least-privilege role in ../bootstrap.
# See docs/build-journey.md ("Where the AI flow diverged from the tutorial").
#
# Tutorial says:
#   - Attach AmazonS3FullAccess + AmazonEC2FullAccess (managed policies)
#   - Name the role 'spacelift-orbit-labs-role'
#   - Description: 'Role for Spacelift to manage AWS infrastructure'
#
# The trust policy is the same Spacelift AssumeRole + TagSession pattern the
# least-privilege role uses (that's what makes the role assumable by Spacelift).

locals {
  spacelift_issuer_host = var.spacelift_issuer_host
  spacelift_issuer_url  = "https://${local.spacelift_issuer_host}"
}

data "aws_iam_openid_connect_provider" "spacelift" {
  # Reuse the OIDC provider already created by ../bootstrap (don't recreate it).
  url = local.spacelift_issuer_url
}

data "aws_iam_policy_document" "trust" {
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

  statement {
    sid     = "SpaceliftTagSession"
    effect  = "Allow"
    actions = ["sts:TagSession"]
    principals {
      type        = "AWS"
      identifiers = [var.spacelift_aws_account_id]
    }
  }

  statement {
    sid     = "SpaceliftWebIdentity"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity", "sts:TagSession"]
    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.spacelift.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.spacelift_issuer_host}:aud"
      values   = [local.spacelift_issuer_url]
    }
    condition {
      test     = "StringLike"
      variable = "${local.spacelift_issuer_host}:sub"
      values   = ["space:*:stack:*:run_type:*:scope:*"]
    }
  }
}

resource "aws_iam_role" "tutorial" {
  name               = "spacelift-orbit-labs-role"
  description        = "Role for Spacelift to manage AWS infrastructure"
  assume_role_policy = data.aws_iam_policy_document.trust.json

  tags = {
    Project   = "spacelift-gitops-demo"
    ManagedBy = "opentofu-bootstrap-tutorial-role"
    Note      = "tutorial-exact-role-broad-managed-policies"
  }
}

# The two managed policies the tutorial prescribes (broad; not least-privilege).
resource "aws_iam_role_policy_attachment" "s3" {
  role       = aws_iam_role.tutorial.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_iam_role_policy_attachment" "ec2" {
  role       = aws_iam_role.tutorial.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2FullAccess"
}
