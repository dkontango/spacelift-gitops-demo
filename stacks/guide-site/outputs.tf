output "website_endpoint" {
  description = "The public S3 static-website URL of the onboarding guide."
  value       = "http://${aws_s3_bucket_website_configuration.site.website_endpoint}"
}

output "bucket_name" {
  description = "Name of the guide-site bucket."
  value       = aws_s3_bucket.site.id
}

output "file_count" {
  description = "Number of site files uploaded."
  value       = length(local.site_files)
}
