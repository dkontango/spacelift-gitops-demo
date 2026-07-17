package spacelift

# Unit tests for plan-block-public-s3.rego. Run: opa test policies/ --v1-compatible

private_pab := {"terraform": {"resource_changes": [{
	"address": "module.app_bucket.aws_s3_bucket_public_access_block.this",
	"type": "aws_s3_bucket_public_access_block",
	"change": {
		"actions": ["create"],
		"after": {
			"block_public_acls": true,
			"block_public_policy": true,
			"ignore_public_acls": true,
			"restrict_public_buckets": true,
		},
	},
}]}}

public_pab := {"terraform": {"resource_changes": [{
	"address": "module.app_bucket.aws_s3_bucket_public_access_block.this",
	"type": "aws_s3_bucket_public_access_block",
	"change": {
		"actions": ["create"],
		"after": {
			"block_public_acls": false,
			"block_public_policy": false,
			"ignore_public_acls": false,
			"restrict_public_buckets": false,
		},
	},
}]}}

test_private_bucket_allowed if {
	count(deny) == 0 with input as private_pab
}

test_public_bucket_denied if {
	count(deny) == 1 with input as public_pab
}
