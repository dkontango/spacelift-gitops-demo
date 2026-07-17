# Proves which AWS identity Spacelift assumed on each run (via OIDC/AssumeRole),
# surfacing the account id in the run outputs.
data "aws_caller_identity" "current" {}

locals {
  name_prefix = "spacelift-gitops-demo-${var.environment}"
  common_tags = {
    Project     = "spacelift-gitops-demo"
    Environment = var.environment
    ManagedBy   = "spacelift-opentofu"
  }
}

# Prod uses the same module as dev — the promotion story is "the same code, gated
# by an Approval policy before it applies to prod." In the paid tier, prod would
# consume dev's name_prefix output via a Spacelift stack dependency; on free tier
# the dependency is narrated and the prefix is derived locally.
module "app_bucket" {
  source     = "../../modules/s3-bucket"
  name       = "${local.name_prefix}-app-${var.bucket_suffix}"
  public     = false
  versioning = true
  tags       = local.common_tags
}
