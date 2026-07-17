locals {
  common_tags = {
    project     = "spacelift-gitops-demo"
    environment = var.environment
    managed_by  = "spacelift-opentofu"
  }
}

# A stand-in for a real resource, using only credential-less providers so the
# stack needs NO cloud integration. random_pet gives each apply a stable,
# human-readable name; the null_resource carries the demo's "visibility" flag
# so the Plan policy has something to inspect (see policies/plan-sandbox-*).
resource "random_pet" "name" {
  length = 2
  keepers = {
    environment = var.environment
  }
}

resource "null_resource" "app" {
  triggers = {
    name       = "spacelift-gitops-demo-${var.environment}-${random_pet.name.id}"
    visibility = var.make_public ? "public" : "private"
    tags       = jsonencode(local.common_tags)
  }
}

# Added per the Spacelift tutorial, alongside the random_pet resource. This data
# source forces the run to authenticate to AWS — so it will exercise (and prove)
# the AWS cloud integration on this stack, surfacing the account id as an output.
data "aws_caller_identity" "current" {}
