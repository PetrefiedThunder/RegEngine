# Generate random passwords
resource "random_password" "admin_master_key" {
  length  = 32
  special = false
}

resource "random_password" "neo4j_password" {
  length  = 24
  special = true
}

# Admin Master Key
resource "aws_secretsmanager_secret" "admin_master_key" {
  name        = "${var.project_name}/${var.environment}/admin-master-key"
  description = "Admin API master key for managing API keys"

  tags = {
    Service = "admin-api"
  }
}

resource "aws_secretsmanager_secret_version" "admin_master_key" {
  secret_id     = aws_secretsmanager_secret.admin_master_key.id
  secret_string = random_password.admin_master_key.result
}

# Neo4j Password
resource "aws_secretsmanager_secret" "neo4j_password" {
  name        = "${var.project_name}/${var.environment}/neo4j-password"
  description = "Neo4j database password"

  tags = {
    Service = "neo4j"
  }
}

resource "aws_secretsmanager_secret_version" "neo4j_password" {
  secret_id     = aws_secretsmanager_secret.neo4j_password.id
  secret_string = random_password.neo4j_password.result
}
