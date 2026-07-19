# Deploys the onboarding guide as an S3 static website. The site itself is
# deployed by the very GitOps pipeline it documents (Forgejo -> GitHub ->
# Spacelift -> AWS). The repo stays private; only the rendered site is public.

locals {
  # Map each site file to its content-type by extension.
  content_types = {
    "html" = "text/html"
    "css"  = "text/css"
    "js"   = "application/javascript"
    "png"  = "image/png"
    "svg"  = "image/svg+xml"
    "mp4"  = "video/mp4"
    "json" = "application/json"
    "txt"  = "text/plain"
  }
  # All web files under the site dir (exclude the build script and any non-web
  # artifacts). Relative paths become S3 keys.
  all_files  = fileset(var.site_dir, "**")
  site_files = [for f in local.all_files : f if !endswith(f, ".py")]
}

resource "aws_s3_bucket" "site" {
  bucket_prefix = var.bucket_prefix
  tags = {
    project = "spacelift-gitops-demo"
    purpose = "onboarding-guide-static-site"
  }
}

# Static website hosting.
resource "aws_s3_bucket_website_configuration" "site" {
  bucket = aws_s3_bucket.site.id
  index_document { suffix = "index.html" }
  error_document { key = "index.html" }
}

# This bucket is INTENTIONALLY public-read (it hosts a public website). The
# plan-block-public-s3 policy is deliberately NOT attached to this stack — a
# public website bucket is the one legitimate case for public access. That
# distinction (guardrail on data buckets, exception for website buckets) is
# itself worth calling out in a demo.
resource "aws_s3_bucket_public_access_block" "site" {
  bucket                  = aws_s3_bucket.site.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "public_read" {
  bucket     = aws_s3_bucket.site.id
  depends_on = [aws_s3_bucket_public_access_block.site]
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicReadGetObject"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.site.arn}/*"
    }]
  })
}

# Upload every site file with the right content-type; re-upload when it changes.
resource "aws_s3_object" "site" {
  for_each = { for f in local.site_files : f => f }

  bucket       = aws_s3_bucket.site.id
  key          = each.value
  source       = "${var.site_dir}/${each.value}"
  etag         = filemd5("${var.site_dir}/${each.value}")
  content_type = lookup(local.content_types, lower(reverse(split(".", each.value))[0]), "application/octet-stream")
}
