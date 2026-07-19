terraform {
  required_version = ">= 1.6.0" # floor; tested with OpenTofu 1.12.4 (latest), which Spacelift runs
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
  # Spacelift manages state. Credentials come from the AWS cloud integration
  # (OIDC/AssumeRole) attached to this stack — no static keys.
}

provider "aws" {
  region = var.aws_region
}
