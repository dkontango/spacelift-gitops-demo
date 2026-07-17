variable "name" {
  description = "Bucket name (globally unique). The demo prefixes this with the environment."
  type        = string
}

variable "tags" {
  description = "Tags applied to the bucket."
  type        = map(string)
  default     = {}
}

variable "public" {
  description = <<-EOT
    Whether the bucket allows public access. Default false (all four public-access
    blocks ON). Setting this true is the change the Plan policy is designed to
    DENY — it is the demo's guardrail hook, not something you'd normally enable.
  EOT
  type    = bool
  default = false
}

variable "versioning" {
  description = "Enable S3 bucket versioning."
  type        = bool
  default     = true
}
