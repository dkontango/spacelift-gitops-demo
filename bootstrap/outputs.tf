output "role_arn" {
  description = "ARN of the IAM role Spacelift assumes. Paste this into the Spacelift AWS Cloud Integration."
  value       = aws_iam_role.spacelift.arn
}

output "oidc_provider_arn" {
  description = "ARN of the registered Spacelift OIDC provider."
  value       = aws_iam_openid_connect_provider.spacelift.arn
}

output "next_step" {
  description = "What to do with these outputs."
  value       = "In Spacelift: Settings > Cloud integrations > AWS > add integration, paste role_arn, then attach the integration to each stack. No AWS keys go into Spacelift."
}
