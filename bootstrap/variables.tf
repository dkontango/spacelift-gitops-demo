variable "aws_region" {
  description = "AWS region for the bootstrap (IAM is global, but the provider needs a region)."
  type        = string
  default     = "us-east-1"
}

variable "spacelift_issuer_host" {
  description = <<-EOT
    Full Spacelift OIDC issuer host (no scheme). US region:
    <account>.app.us.spacelift.io ; EU region: <account>.app.spacelift.io.
    For this account: dkontango.app.us.spacelift.io
  EOT
  type = string
}

variable "spacelift_account_name" {
  description = "Spacelift account name (the subdomain), used in the ExternalId condition. This build: dkontango."
  type        = string
}

variable "spacelift_aws_account_id" {
  description = <<-EOT
    AWS account ID of Spacelift's shared public workers, the principal that
    assumes the role via sts:AssumeRole. Shown in the integration's trust-policy
    example in the Spacelift UI. For this account the dialog showed 577638371743.
  EOT
  type    = string
  default = "577638371743"
}

variable "role_name" {
  description = "Name of the IAM role Spacelift will assume via OIDC."
  type        = string
  default     = "spacelift-gitops-demo"
}

variable "bucket_prefix" {
  description = "S3 bucket name prefix the assumed role is permitted to manage."
  type        = string
  default     = "spacelift-gitops-demo"
}

variable "allowed_sub" {
  description = <<-EOT
    OIDC sub condition (StringLike) restricting which Spacelift runs may assume
    the role. Format: space:<space>:stack:<stack>:run_type:<type>:scope:<scope>.
    Default allows any stack in the account; tighten to specific stack IDs.
  EOT
  type    = string
  default = "space:*:stack:*:run_type:*:scope:*"
}

variable "oidc_thumbprints" {
  description = <<-EOT
    TLS thumbprint(s) of the Spacelift OIDC issuer. AWS now validates the
    provider cert against its trusted CAs and largely ignores this, but the
    field is still required. The value below is the well-known root-CA
    thumbprint AWS documents as a safe placeholder; the console's "Get
    thumbprint" fetches the live one.
  EOT
  type    = list(string)
  default = ["9e99a48a9960b14926bb7f3b02e22da2b0ab7280"]
}
