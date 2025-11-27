###############################################################################
# ECR Repository for Lambda Container Images
###############################################################################

resource "aws_ecr_repository" "lambda" {
  name                 = "${var.project_name}-lambda-${var.environment}"
  image_tag_mutability = "IMMUTABLE"  # Prevent overwriting tags for safe rollbacks

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-lambda-${var.environment}"
    Component = "container-registry"
  })
}

# Lifecycle policy to keep recent images for rollback support
resource "aws_ecr_lifecycle_policy" "lambda" {
  repository = aws_ecr_repository.lambda.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 20 versioned images for rollback"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v", "sha-"]
          countType     = "imageCountMoreThan"
          countNumber   = 20
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Expire untagged images after 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# Repository policy to allow Lambda service to pull images
resource "aws_ecr_repository_policy" "lambda" {
  repository = aws_ecr_repository.lambda.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "LambdaECRImageRetrievalPolicy"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
      }
    ]
  })
}

# Output ECR repository URL
output "ecr_repository_url" {
  description = "ECR repository URL for Lambda container images"
  value       = aws_ecr_repository.lambda.repository_url
}
