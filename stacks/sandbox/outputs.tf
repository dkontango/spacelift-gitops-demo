output "resource_name" {
  description = "Generated name of the simulated resource."
  value       = null_resource.app.triggers.name
}

output "visibility" {
  description = "public or private — the value the sandbox Plan policy checks."
  value       = null_resource.app.triggers.visibility
}
