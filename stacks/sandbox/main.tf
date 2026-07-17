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
