output "name_prefix" {
  description = "Naming prefix for this environment. In the paid tier the prod stack consumes this via a stack dependency; here it documents the promotion contract."
  value       = local.name_prefix
}

output "app_bucket_arn" {
  description = "ARN of the dev app bucket."
  value       = module.app_bucket.arn
}

output "aws_account_id" {
  description = "AWS account id the run authenticated into (proves the assumed identity)."
  value       = data.aws_caller_identity.current.account_id
}
