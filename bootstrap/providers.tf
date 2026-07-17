terraform {
  required_version = ">= 1.6.0"
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
