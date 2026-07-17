terraform {
  required_version = ">= 1.6.0" # floor; tested with OpenTofu 1.12.4 (latest), which Spacelift runs
  required_providers {
    # Credential-less providers: the sandbox started with no cloud account.
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
    # AWS added per the Spacelift tutorial. NOTE: once the aws_caller_identity
    # data source below is present, this stack must have an AWS cloud integration
    # attached — it can no longer run with zero credentials. This is the step
    # where the approval-free sandbox transitions into needing real AWS access.
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
  # Spacelift manages state.
}

provider "aws" {
  region = "us-east-1"
}
