variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "spacelift_issuer_host" {
  description = "Full Spacelift OIDC issuer host, e.g. dkontango.app.us.spacelift.io"
  type        = string
}

variable "spacelift_account_name" {
  description = "Spacelift account name (subdomain), used in the ExternalId condition."
  type        = string
}

variable "spacelift_aws_account_id" {
  description = "Spacelift shared-worker AWS account id (us.spacelift.io = 577638371743)."
  type        = string
  default     = "577638371743"
}
