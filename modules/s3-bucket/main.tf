resource "aws_s3_bucket" "this" {
  bucket = var.name
  tags   = var.tags
}

# The public-access block is the lever the Plan policy inspects. When public =
# false (the default and the safe state) all four protections are ON. Flipping
# public = true disables them — which the plan-block-public-s3 policy DENIES.
resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = !var.public
  block_public_policy     = !var.public
  ignore_public_acls      = !var.public
  restrict_public_buckets = !var.public
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  versioning_configuration {
    status = var.versioning ? "Enabled" : "Suspended"
  }
}
