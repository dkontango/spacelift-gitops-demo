terraform {
  required_version = ">= 1.6.0" # floor; tested with OpenTofu 1.12.4 (latest), which Spacelift runs
  required_providers {
    # Credential-less providers: no cloud account, no IAM, no approval needed.
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
  # Spacelift manages state. No cloud integration is attached to this stack —
  # that is the whole point: you can evaluate the full GitOps + policy workflow
  # with zero cloud credentials and zero IAM changes to approve.
}
