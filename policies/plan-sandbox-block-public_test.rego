package spacelift

# Tests for plan-sandbox-block-public.rego. Run: opa test policies/ --v1-compatible

private_res := {"terraform": {"resource_changes": [{
	"address": "null_resource.app",
	"type": "null_resource",
	"change": {"actions": ["create"], "after": {"triggers": {"visibility": "private"}}},
}]}}

public_res := {"terraform": {"resource_changes": [{
	"address": "null_resource.app",
	"type": "null_resource",
	"change": {"actions": ["create"], "after": {"triggers": {"visibility": "public"}}},
}]}}

test_sandbox_private_allowed if {
	count(deny) == 0 with input as private_res
}

test_sandbox_public_denied if {
	count(deny) == 1 with input as public_res
}
