terraform {
  required_version = ">= 1.6.0" # floor; tested with OpenTofu 1.12.4 (latest), which Spacelift runs
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Credentials are supplied by the environment (env vars / shared config) at
# apply time — this bootstrap is run ONCE locally with admin AWS keys. It is the
# only place static keys are used; everything downstream is OIDC.
provider "aws" {
  region = var.aws_region
}
