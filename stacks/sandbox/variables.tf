variable "environment" {
  description = "Environment label for generated names."
  type        = string
  default     = "sandbox"
}

variable "make_public" {
  description = <<-EOT
    Demo lever mirroring the S3 "public bucket" scenario, but with no cloud.
    When true, the config marks the simulated resource as public — which the
    sandbox Plan policy DENIES. Lets you show policy-as-code blocking a risky
    change with zero cloud credentials.
  EOT
  type    = bool
  default = true # E2E demo: flip bucket public to trigger the OPA plan policy DENY
}
