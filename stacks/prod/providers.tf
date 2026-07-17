terraform {
  required_version = ">= 1.6.0" # floor; tested with OpenTofu 1.12.4 (latest), which Spacelift runs
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
  # No backend block: Spacelift provides managed state. Credentials come from the
  # Spacelift AWS Cloud Integration (OIDC) attached to this stack.
}

provider "aws" {
  region = var.aws_region
}
