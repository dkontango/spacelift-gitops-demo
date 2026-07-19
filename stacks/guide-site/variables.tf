variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "bucket_prefix" {
  description = "Prefix for the guide-site bucket. AWS appends a unique suffix."
  type        = string
  default     = "spacelift-guide-site-"
}

variable "site_dir" {
  description = "Path (relative to this stack root) to the built static site."
  type        = string
  default     = "../../site"
}
