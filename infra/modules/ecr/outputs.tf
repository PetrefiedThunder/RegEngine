output "admin_api_repository_url" {
  description = "Admin API ECR repository URL"
  value       = aws_ecr_repository.admin_api.repository_url
}

output "ingestion_repository_url" {
  description = "Ingestion service ECR repository URL"
  value       = aws_ecr_repository.ingestion.repository_url
}

output "nlp_repository_url" {
  description = "NLP service ECR repository URL"
  value       = aws_ecr_repository.nlp.repository_url
}

output "graph_repository_url" {
  description = "Graph service ECR repository URL"
  value       = aws_ecr_repository.graph.repository_url
}

output "opportunity_repository_url" {
  description = "Opportunity API ECR repository URL"
  value       = aws_ecr_repository.opportunity.repository_url
}
