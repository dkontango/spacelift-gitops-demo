output "name_prefix" {
  description = "Naming prefix for the prod environment."
  value       = local.name_prefix
}

output "app_bucket_arn" {
  description = "ARN of the prod app bucket."
  value       = module.app_bucket.arn
}
