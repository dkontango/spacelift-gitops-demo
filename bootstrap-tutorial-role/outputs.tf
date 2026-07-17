output "tutorial_role_arn" {
  description = "ARN of the tutorial-exact role (spacelift-orbit-labs-role). Paste into a Spacelift AWS integration to follow the tutorial literally."
  value       = aws_iam_role.tutorial.arn
}
