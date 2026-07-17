locals {
  name_prefix = "spacelift-gitops-demo-${var.environment}"
  common_tags = {
    Project     = "spacelift-gitops-demo"
    Environment = var.environment
    ManagedBy   = "spacelift-opentofu"
  }
}

# The demo's baseline resource. In the video, the "change" on a PR is editing
# this block (add a tag, add a second bucket, or flip public = true to trip the
# Plan policy).
module "app_bucket" {
  source     = "../../modules/s3-bucket"
  name       = "${local.name_prefix}-app-${var.bucket_suffix}"
  public     = false
  versioning = true
  tags       = local.common_tags
}
