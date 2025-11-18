terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment for remote state
  # backend "s3" {
  #   bucket         = "regengine-terraform-state"
  #   key            = "prod/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-state-lock"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = var.tags
  }
}

# VPC and Networking
module "vpc" {
  source = "./modules/vpc"

  project_name         = var.project_name
  environment          = var.environment
  vpc_cidr             = var.vpc_cidr
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
}

# Security Groups
module "security_groups" {
  source = "./modules/security-groups"

  project_name = var.project_name
  environment  = var.environment
  vpc_id       = module.vpc.vpc_id
}

# Application Load Balancer
module "alb" {
  source = "./modules/alb"

  project_name        = var.project_name
  environment         = var.environment
  vpc_id              = module.vpc.vpc_id
  public_subnet_ids   = module.vpc.public_subnet_ids
  security_group_ids  = [module.security_groups.alb_sg_id]
}

# S3 Buckets
module "s3" {
  source = "./modules/s3"

  project_name         = var.project_name
  environment          = var.environment
  enable_versioning    = var.enable_s3_versioning
  lifecycle_days       = var.s3_lifecycle_days
}

# Secrets Manager
module "secrets" {
  source = "./modules/secrets"

  project_name = var.project_name
  environment  = var.environment
}

# IAM Roles
module "iam" {
  source = "./modules/iam"

  project_name         = var.project_name
  environment          = var.environment
  raw_bucket_arn       = module.s3.raw_bucket_arn
  processed_bucket_arn = module.s3.processed_bucket_arn
  secret_arns          = module.secrets.secret_arns
}

# MSK (Managed Kafka)
module "kafka" {
  source = "./modules/kafka"

  project_name        = var.project_name
  environment         = var.environment
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  security_group_ids  = [module.security_groups.kafka_sg_id]
  instance_type       = var.kafka_instance_type
  broker_count        = var.kafka_broker_count
}

# Neo4j Graph Database
module "neo4j" {
  source = "./modules/neo4j"

  project_name       = var.project_name
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  security_group_ids = [module.security_groups.neo4j_sg_id]
  instance_type      = var.neo4j_instance_type
  neo4j_password_arn = module.secrets.neo4j_password_arn
}

# ECR Repositories
module "ecr" {
  source = "./modules/ecr"

  project_name = var.project_name
  environment  = var.environment
}

# ECS Cluster
module "ecs_cluster" {
  source = "./modules/ecs-cluster"

  project_name              = var.project_name
  environment               = var.environment
  enable_container_insights = var.enable_container_insights
}

# ECS Services will be added in separate module files due to length
