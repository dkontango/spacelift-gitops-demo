package spacelift

# Push policy — scopes each stack to its own directory so a change to one
# environment doesn't needlessly trigger the others, and implements the GitOps
# trigger model:
#   - push to a feature branch that touches this stack's dir  -> PROPOSE (preview)
#   - push to the default branch that touches this stack's dir -> TRACK (deploy)
#   - anything not touching this stack's dir                   -> IGNORE
#
# Attach to every stack. Because each stack has its own project_root
# (stacks/dev, stacks/prod), the same policy routes pushes to the right stack.
#
# Input schema: input.push.affected_files[], input.push.branch,
# input.stack.branch, input.stack.project_root.

track if {
	affected
	input.push.branch == input.stack.branch
}

propose if {
	affected
	input.push.branch != input.stack.branch
}

ignore if {
	not affected
}

# A change is relevant to this stack if it touches the stack's project root or
# the shared module the stacks consume.
affected if {
	some filepath in input.push.affected_files
	startswith(filepath, input.stack.project_root)
}

affected if {
	some filepath in input.push.affected_files
	startswith(filepath, "modules/")
}
