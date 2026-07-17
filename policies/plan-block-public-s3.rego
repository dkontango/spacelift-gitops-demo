package spacelift

# Plan policy — the demo's headline guardrail.
#
# DENY any run whose plan would create or update an S3 bucket into a PUBLIC
# state, i.e. an aws_s3_bucket_public_access_block that turns any of the four
# protections off. This is exactly the change a developer makes on the "bad" PR
# in the demo, and Spacelift blocks it in the PR preview before it can merge.
#
# WARN (does not block, but flags for human review) when a run deletes an S3
# bucket — a heads-up that data could be lost.
#
# Input schema: input.terraform.resource_changes[] with .type, .address,
# .change.actions[] and .change.after (the planned attributes).

deny contains msg if {
	some rc in input.terraform.resource_changes
	rc.type == "aws_s3_bucket_public_access_block"

	some action in rc.change.actions
	action in {"create", "update"}

	# Any protection turned off => the bucket is being made public-capable.
	after := rc.change.after
	not all_protections_enabled(after)

	msg := sprintf(
		"S3 public access is not allowed: %s disables one or more public-access-block protections. Set the bucket's public=false.",
		[rc.address],
	)
}

warn contains msg if {
	some rc in input.terraform.resource_changes
	rc.type == "aws_s3_bucket"

	some action in rc.change.actions
	action == "delete"

	msg := sprintf("S3 bucket is being destroyed: %s. Confirm this is intentional.", [rc.address])
}

all_protections_enabled(after) if {
	after.block_public_acls == true
	after.block_public_policy == true
	after.ignore_public_acls == true
	after.restrict_public_buckets == true
}
