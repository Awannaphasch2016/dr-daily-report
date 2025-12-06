# Aurora MySQL Serverless v2 for Ticker Data Storage
#
# Architecture:
#   - Aurora MySQL Serverless v2 cluster (0.5-2 ACU for cost optimization)
#   - Private subnets with Lambda-only access via security group
#   - Stores structured ticker data fetched from Yahoo Finance
#   - Future: Legacy SQL data migration
#
# Tables:
#   - daily_prices: Historical OHLCV data
#   - ticker_info: Company metadata and mappings
#
# Cost Estimate:
#   - 0.5 ACU minimum: ~$43/month
#   - Storage: $0.10/GB/month
#   - I/O: $0.20 per million requests

###############################################################################
# Variables
###############################################################################

variable "aurora_enabled" {
  description = "Enable Aurora MySQL cluster (set to false to skip creation)"
  type        = bool
  default     = false  # Start disabled, enable when ready
}

variable "aurora_min_acu" {
  description = "Minimum ACU capacity for Aurora Serverless v2 (0.5 ACU = ~$43/month)"
  type        = number
  default     = 0.5
}

variable "aurora_max_acu" {
  description = "Maximum ACU capacity for Aurora Serverless v2"
  type        = number
  default     = 2
}

variable "aurora_master_username" {
  description = "Master username for Aurora cluster"
  type        = string
  default     = "admin"
}

variable "AURORA_MASTER_PASSWORD" {
  description = "Master password for Aurora cluster"
  type        = string
  sensitive   = true
  default     = ""  # Will be set via Doppler TF_VAR_AURORA_MASTER_PASSWORD
}

variable "aurora_database_name" {
  description = "Initial database name"
  type        = string
  default     = "ticker_data"
}

###############################################################################
# Security Group for Aurora
###############################################################################

resource "aws_security_group" "aurora" {
  count = var.aurora_enabled ? 1 : 0

  name        = "${var.project_name}-aurora-${var.environment}"
  description = "Security group for Aurora MySQL cluster"
  vpc_id      = data.aws_vpc.default.id

  # Allow MySQL access from Lambda security group
  ingress {
    description     = "MySQL from Lambda"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_aurora[0].id]
  }

  # Allow access from within VPC (for local testing via bastion if needed)
  ingress {
    description = "MySQL from VPC"
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.default.cidr_block]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-aurora-sg"
    App       = "shared"
    Component = "aurora-security-group"
  })
}

# Security group for Lambda functions that need Aurora access
resource "aws_security_group" "lambda_aurora" {
  count = var.aurora_enabled ? 1 : 0

  name        = "${var.project_name}-lambda-aurora-${var.environment}"
  description = "Security group for Lambda functions accessing Aurora"
  vpc_id      = data.aws_vpc.default.id

  # Allow all outbound traffic (needed for Aurora, S3, external APIs)
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-lambda-aurora-sg"
    App       = "shared"
    Component = "lambda-security-group"
  })
}

###############################################################################
# Data Sources
###############################################################################

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

###############################################################################
# Private Subnets with NAT Gateway Routes
###############################################################################
# Lambda functions in VPC need internet access (yfinance, OpenRouter, DynamoDB).
# Only these 3 subnets have routes to NAT Gateway (rtb-08f039fbeec97fd35).
# The other 3 subnets use the main route table with IGW - Lambda can't use IGW
# because it doesn't get a public IP.
#
# Subnets with NAT route (0.0.0.0/0 -> nat-0ddc2f2ba2848e433):
#   - subnet-0bfaf6ef0e1a456a6 (ap-southeast-1a)
#   - subnet-0ef493a1aae3b4af4 (ap-southeast-1c)
#   - subnet-012d60cbb95430cd6 (ap-southeast-1b)
#
# Subnets WITHOUT NAT route (Lambda will timeout if placed here):
#   - subnet-0da9ef11b7da7ce3a (ap-southeast-1a) - has NAT Gateway, but uses IGW route
#   - subnet-030760a3f13e4eacc (ap-southeast-1c) - has Aurora RDS
#   - subnet-0e3861e4ea942da39 (ap-southeast-1b) - has ElasticSearch

locals {
  # Only use subnets that have NAT Gateway routes for Lambda
  # This ensures Lambda can reach external APIs (yfinance, OpenRouter)
  private_subnets_with_nat = [
    "subnet-0bfaf6ef0e1a456a6", # ap-southeast-1a
    "subnet-0ef493a1aae3b4af4", # ap-southeast-1c
    "subnet-012d60cbb95430cd6", # ap-southeast-1b
  ]
}

###############################################################################
# DB Subnet Group
###############################################################################

resource "aws_db_subnet_group" "aurora" {
  count = var.aurora_enabled ? 1 : 0

  name        = "${var.project_name}-aurora-${var.environment}"
  description = "Subnet group for Aurora cluster"
  subnet_ids  = data.aws_subnets.default.ids

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-aurora-subnet-group"
    App       = "shared"
    Component = "aurora-subnet-group"
  })
}

###############################################################################
# Aurora Serverless v2 Cluster
###############################################################################

resource "aws_rds_cluster" "aurora" {
  count = var.aurora_enabled ? 1 : 0

  cluster_identifier = "${var.project_name}-aurora-${var.environment}"
  engine             = "aurora-mysql"
  engine_mode        = "provisioned"
  engine_version     = "8.0.mysql_aurora.3.04.0"
  database_name      = var.aurora_database_name
  master_username    = var.aurora_master_username
  master_password    = var.AURORA_MASTER_PASSWORD

  db_subnet_group_name   = aws_db_subnet_group.aurora[0].name
  vpc_security_group_ids = [aws_security_group.aurora[0].id]

  # Serverless v2 capacity configuration
  serverlessv2_scaling_configuration {
    min_capacity = var.aurora_min_acu
    max_capacity = var.aurora_max_acu
  }

  # Backup and maintenance
  backup_retention_period = 7
  preferred_backup_window = "02:00-03:00"  # 09:00-10:00 Bangkok time

  # Skip final snapshot for dev (enable for prod)
  skip_final_snapshot       = var.environment == "dev" ? true : false
  final_snapshot_identifier = var.environment == "dev" ? null : "${var.project_name}-aurora-final-${var.environment}"

  # Enable deletion protection in prod
  deletion_protection = var.environment == "prod" ? true : false

  # Enable enhanced monitoring
  enabled_cloudwatch_logs_exports = ["error", "slowquery"]

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-aurora-cluster"
    App       = "shared"
    Component = "aurora-cluster"
  })
}

###############################################################################
# Aurora Serverless v2 Instance
###############################################################################

resource "aws_rds_cluster_instance" "aurora" {
  count = var.aurora_enabled ? 1 : 0

  identifier         = "${var.project_name}-aurora-instance-${var.environment}"
  cluster_identifier = aws_rds_cluster.aurora[0].id
  instance_class     = "db.serverless"  # Required for Serverless v2
  engine             = aws_rds_cluster.aurora[0].engine
  engine_version     = aws_rds_cluster.aurora[0].engine_version

  # Performance insights (optional, adds ~$0.60/month for 7-day retention)
  performance_insights_enabled          = var.environment == "prod" ? true : false
  performance_insights_retention_period = var.environment == "prod" ? 7 : null

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-aurora-instance"
    App       = "shared"
    Component = "aurora-instance"
  })
}

###############################################################################
# IAM Policy for Lambda to access Secrets Manager (for DB credentials)
###############################################################################

resource "aws_iam_policy" "lambda_aurora_access" {
  count = var.aurora_enabled ? 1 : 0

  name        = "${var.project_name}-lambda-aurora-access-${var.environment}"
  description = "Allow Lambda to access Aurora cluster"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "rds:DescribeDBClusters",
          "rds:DescribeDBInstances"
        ]
        Resource = aws_rds_cluster.aurora[0].arn
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:AssignPrivateIpAddresses",
          "ec2:UnassignPrivateIpAddresses"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-lambda-aurora-policy"
    App       = "shared"
    Component = "iam-policy"
  })
}

###############################################################################
# Store DB Credentials in Secrets Manager
###############################################################################

resource "aws_secretsmanager_secret" "aurora_credentials" {
  count = var.aurora_enabled ? 1 : 0

  name        = "${var.project_name}/aurora/${var.environment}"
  description = "Aurora MySQL credentials for ${var.project_name}"

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-aurora-credentials"
    App       = "shared"
    Component = "secrets-manager"
  })
}

resource "aws_secretsmanager_secret_version" "aurora_credentials" {
  count = var.aurora_enabled ? 1 : 0

  secret_id = aws_secretsmanager_secret.aurora_credentials[0].id
  secret_string = jsonencode({
    username = var.aurora_master_username
    password = var.AURORA_MASTER_PASSWORD
    host     = aws_rds_cluster.aurora[0].endpoint
    port     = 3306
    database = var.aurora_database_name
  })
}

###############################################################################
# Outputs
###############################################################################

output "aurora_cluster_endpoint" {
  description = "Aurora cluster endpoint for writes"
  value       = var.aurora_enabled ? aws_rds_cluster.aurora[0].endpoint : null
}

output "aurora_cluster_reader_endpoint" {
  description = "Aurora cluster reader endpoint for reads"
  value       = var.aurora_enabled ? aws_rds_cluster.aurora[0].reader_endpoint : null
}

output "aurora_cluster_port" {
  description = "Aurora cluster port"
  value       = var.aurora_enabled ? aws_rds_cluster.aurora[0].port : null
}

output "aurora_security_group_id" {
  description = "Security group ID for Aurora cluster"
  value       = var.aurora_enabled ? aws_security_group.aurora[0].id : null
}

output "lambda_aurora_security_group_id" {
  description = "Security group ID for Lambda functions accessing Aurora"
  value       = var.aurora_enabled ? aws_security_group.lambda_aurora[0].id : null
}

output "aurora_credentials_secret_arn" {
  description = "ARN of the Secrets Manager secret containing Aurora credentials"
  value       = var.aurora_enabled ? aws_secretsmanager_secret.aurora_credentials[0].arn : null
}
