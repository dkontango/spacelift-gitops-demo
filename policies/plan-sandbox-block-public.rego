package spacelift

# Sandbox Plan policy — the credential-free analogue of plan-block-public-s3.
# DENY any plan where the simulated resource is marked "public". Demonstrates
# policy-as-code blocking a risky change with NO cloud provider involved.
#
# Input schema: input.terraform.resource_changes[] with .type, .address, and
# .change.after (the planned attributes). For null_resource, the demo's
# visibility flag lives in .change.after.triggers.visibility.

deny contains msg if {
	some rc in input.terraform.resource_changes
	rc.type == "null_resource"

	some action in rc.change.actions
	action in {"create", "update"}

	rc.change.after.triggers.visibility == "public"

	msg := sprintf(
		"Public resources are not allowed in the sandbox: %s is marked public. Set make_public = false.",
		[rc.address],
	)
}
