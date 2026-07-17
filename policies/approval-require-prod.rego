package spacelift

# Approval policy — the governance beat in the demo.
#
# Auto-approve runs on non-production stacks (dev flows straight through).
# Require at least one human approval, and zero rejections, before a production
# stack can apply. Attach this policy to the stacks and label the prod stack
# "production".
#
# Input schema: input.stack.labels[], input.reviews.current.approvals[] /
# .rejections[], input.run.type.

# Non-production: no manual approval required.
approve if {
	not is_production
}

# Production: needs at least one approval and no rejections.
approve if {
	is_production
	count(input.reviews.current.approvals) >= 1
	count(input.reviews.current.rejections) == 0
}

# A single rejection stops the run outright.
reject if {
	count(input.reviews.current.rejections) > 0
}

is_production if {
	"production" in input.stack.labels
}
