# ECR Repositories for each service
resource "aws_ecr_repository" "admin_api" {
  name                 = "${var.project_name}/${var.environment}/admin-api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Service = "admin-api"
  }
}

resource "aws_ecr_repository" "ingestion" {
  name                 = "${var.project_name}/${var.environment}/ingestion"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Service = "ingestion"
  }
}

resource "aws_ecr_repository" "nlp" {
  name                 = "${var.project_name}/${var.environment}/nlp"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Service = "nlp"
  }
}

resource "aws_ecr_repository" "graph" {
  name                 = "${var.project_name}/${var.environment}/graph"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Service = "graph"
  }
}

resource "aws_ecr_repository" "opportunity" {
  name                 = "${var.project_name}/${var.environment}/opportunity-api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Service = "opportunity-api"
  }
}

# Lifecycle policies
resource "aws_ecr_lifecycle_policy" "main" {
  for_each = {
    admin_api   = aws_ecr_repository.admin_api.name
    ingestion   = aws_ecr_repository.ingestion.name
    nlp         = aws_ecr_repository.nlp.name
    graph       = aws_ecr_repository.graph.name
    opportunity = aws_ecr_repository.opportunity.name
  }

  repository = each.value

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus     = "any"
        countType     = "imageCountMoreThan"
        countNumber   = 10
      }
      action = {
        type = "expire"
      }
    }]
  })
}
