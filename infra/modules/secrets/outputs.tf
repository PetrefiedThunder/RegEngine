output "admin_master_key_arn" {
  description = "Admin master key secret ARN"
  value       = aws_secretsmanager_secret.admin_master_key.arn
  sensitive   = true
}

output "neo4j_password_arn" {
  description = "Neo4j password secret ARN"
  value       = aws_secretsmanager_secret.neo4j_password.arn
  sensitive   = true
}

output "secret_arns" {
  description = "All secret ARNs"
  value = {
    admin_master_key = aws_secretsmanager_secret.admin_master_key.arn
    neo4j_password   = aws_secretsmanager_secret.neo4j_password.arn
  }
  sensitive = true
}

output "admin_master_key_value" {
  description = "Admin master key value (for initial setup only)"
  value       = random_password.admin_master_key.result
  sensitive   = true
}

output "neo4j_password_value" {
  description = "Neo4j password value (for initial setup only)"
  value       = random_password.neo4j_password.result
  sensitive   = true
}
