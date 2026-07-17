variable "aws_region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name, used in bucket naming and tags."
  type        = string
  default     = "dev"
}

variable "bucket_suffix" {
  description = <<-EOT
    Suffix appended to bucket names to keep them globally unique. Buckets are
    named spacelift-gitops-demo-<environment>-<name>-<bucket_suffix>. Must match
    the role's permitted prefix (spacelift-gitops-demo-*).
  EOT
  type    = string
  default = "kontango"
}
