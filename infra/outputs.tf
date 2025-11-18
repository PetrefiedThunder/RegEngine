output "alb_dns_name" {
  description = "Application Load Balancer DNS name"
  value       = module.alb.dns_name
}

output "alb_url" {
  description = "Application Load Balancer URL"
  value       = "https://${module.alb.dns_name}"
}

output "ecr_repositories" {
  description = "ECR repository URLs"
  value = {
    admin_api   = module.ecr.admin_api_repository_url
    ingestion   = module.ecr.ingestion_repository_url
    nlp         = module.ecr.nlp_repository_url
    graph       = module.ecr.graph_repository_url
    opportunity = module.ecr.opportunity_repository_url
  }
}

output "s3_buckets" {
  description = "S3 bucket names"
  value = {
    raw       = module.s3.raw_bucket_name
    processed = module.s3.processed_bucket_name
  }
}

output "kafka_bootstrap_brokers" {
  description = "Kafka bootstrap brokers"
  value       = module.kafka.bootstrap_brokers
  sensitive   = true
}

output "neo4j_connection_uri" {
  description = "Neo4j connection URI"
  value       = module.neo4j.connection_uri
  sensitive   = true
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs_cluster.cluster_name
}

output "secrets_arns" {
  description = "ARNs of secrets in Secrets Manager"
  value       = module.secrets.secret_arns
  sensitive   = true
}

output "deployment_commands" {
  description = "Commands to deploy services"
  value = <<-EOT
    # Build and push Docker images
    aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${module.ecr.admin_api_repository_url}

    docker build -t ${module.ecr.admin_api_repository_url}:latest -f services/admin/Dockerfile .
    docker push ${module.ecr.admin_api_repository_url}:latest

    docker build -t ${module.ecr.ingestion_repository_url}:latest -f services/ingestion/dockerfile .
    docker push ${module.ecr.ingestion_repository_url}:latest

    docker build -t ${module.ecr.nlp_repository_url}:latest -f services/nlp/dockerfile .
    docker push ${module.ecr.nlp_repository_url}:latest

    docker build -t ${module.ecr.graph_repository_url}:latest -f services/graph/dockerfile .
    docker push ${module.ecr.graph_repository_url}:latest

    docker build -t ${module.ecr.opportunity_repository_url}:latest -f services/opportunity/dockerfile .
    docker push ${module.ecr.opportunity_repository_url}:latest

    # Update ECS services
    aws ecs update-service --cluster ${module.ecs_cluster.cluster_name} --service admin-api --force-new-deployment
    aws ecs update-service --cluster ${module.ecs_cluster.cluster_name} --service ingestion --force-new-deployment
    aws ecs update-service --cluster ${module.ecs_cluster.cluster_name} --service nlp --force-new-deployment
    aws ecs update-service --cluster ${module.ecs_cluster.cluster_name} --service graph --force-new-deployment
    aws ecs update-service --cluster ${module.ecs_cluster.cluster_name} --service opportunity-api --force-new-deployment
  EOT
}
