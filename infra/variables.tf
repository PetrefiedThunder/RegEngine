variable "project_name" {
  description = "Project name"
  type        = string
  default     = "regengine"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
}

variable "ecs_task_cpu" {
  description = "ECS task CPU units"
  type        = number
  default     = 512
}

variable "ecs_task_memory" {
  description = "ECS task memory (MiB)"
  type        = number
  default     = 1024
}

variable "ingestion_service_count" {
  description = "Number of ingestion service tasks"
  type        = number
  default     = 2
}

variable "nlp_service_count" {
  description = "Number of NLP service tasks"
  type        = number
  default     = 2
}

variable "graph_service_count" {
  description = "Number of graph service tasks"
  type        = number
  default     = 2
}

variable "opportunity_api_count" {
  description = "Number of opportunity API tasks"
  type        = number
  default     = 2
}

variable "admin_api_count" {
  description = "Number of admin API tasks"
  type        = number
  default     = 1
}

variable "neo4j_instance_type" {
  description = "EC2 instance type for Neo4j"
  type        = string
  default     = "t3.medium"
}

variable "kafka_instance_type" {
  description = "MSK instance type"
  type        = string
  default     = "kafka.m5.large"
}

variable "kafka_broker_count" {
  description = "Number of Kafka brokers"
  type        = number
  default     = 3
}

variable "enable_s3_versioning" {
  description = "Enable S3 bucket versioning"
  type        = bool
  default     = true
}

variable "s3_lifecycle_days" {
  description = "Days before S3 objects transition to IA"
  type        = number
  default     = 90
}

variable "enable_container_insights" {
  description = "Enable ECS Container Insights"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project   = "RegEngine"
    ManagedBy = "Terraform"
  }
}
