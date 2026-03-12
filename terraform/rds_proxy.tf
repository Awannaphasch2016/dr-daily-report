# RDS Proxy for Aurora MySQL Connection Pooling
#
# Architecture:
#   - RDS Proxy sits between Lambda and Aurora
#   - Provides connection multiplexing (46 Lambda clients -> ~10 DB connections)
#   - Enables embarrassingly parallel workloads without connection exhaustion
#
# Benefits:
#   - 5-10x connection multiplexing
#   - Reduced Aurora connection overhead
#   - Faster Lambda connection establishment
#   - Automatic failover handling
#
# Cost Estimate:
#   - ~$0.015 per vCPU-hour
#   - ~$15-25/month for typical usage
#
# Usage:
#   - Update AURORA_HOST in Doppler to use aws_db_proxy.aurora.endpoint
#   - No Lambda code changes required

###############################################################################
# RDS Proxy Configuration
###############################################################################

resource "aws_db_proxy" "aurora" {
  name                   = "${var.project_name}-proxy-${var.environment}"
  debug_logging          = var.environment == "dev" ? true : false
  engine_family          = "MYSQL"
  idle_client_timeout    = 1800  # 30 minutes
  require_tls            = false  # Match current Aurora config
  role_arn               = aws_iam_role.rds_proxy.arn
  vpc_security_group_ids = [aws_security_group.rds_proxy.id]
  vpc_subnet_ids         = local.private_subnets_with_nat

  auth {
    auth_scheme               = "SECRETS"
    client_password_auth_type = "MYSQL_NATIVE_PASSWORD"
    iam_auth                  = "DISABLED"
    secret_arn                = aws_secretsmanager_secret.aurora_credentials.arn
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-rds-proxy"
    App       = "shared"
    Component = "rds-proxy"
  })

  depends_on = [
    aws_iam_role_policy.rds_proxy_secrets,
    aws_secretsmanager_secret_version.aurora_credentials
  ]
}

###############################################################################
# RDS Proxy Target Group
###############################################################################

resource "aws_db_proxy_default_target_group" "aurora" {
  db_proxy_name = aws_db_proxy.aurora.name

  connection_pool_config {
    # Use 100% of available connections for multiplexing
    max_connections_percent = 100

    # Keep 50% of connections idle for fast reuse
    max_idle_connections_percent = 50

    # Wait up to 120 seconds for a connection
    connection_borrow_timeout = 120

    # Session pinning filter (avoid pinning for better multiplexing)
    # EXCLUDE_VARIABLE_SETS allows SET statements without pinning
    session_pinning_filters = ["EXCLUDE_VARIABLE_SETS"]
  }
}

###############################################################################
# RDS Proxy Target (Aurora Cluster)
###############################################################################

resource "aws_db_proxy_target" "aurora" {
  db_proxy_name         = aws_db_proxy.aurora.name
  target_group_name     = aws_db_proxy_default_target_group.aurora.name
  db_cluster_identifier = aws_rds_cluster.aurora.id
}

###############################################################################
# Security Group for RDS Proxy
###############################################################################

resource "aws_security_group" "rds_proxy" {
  name        = "${var.project_name}-rds-proxy-${var.environment}"
  description = "Security group for RDS Proxy"
  vpc_id      = data.aws_vpc.default.id

  # Allow MySQL access from Lambda security group
  ingress {
    description     = "MySQL from Lambda"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_aurora.id]
  }

  # Allow outbound to Aurora
  egress {
    description     = "MySQL to Aurora"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.aurora.id]
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-rds-proxy-sg"
    App       = "shared"
    Component = "rds-proxy-security-group"
  })
}

# Update Aurora security group to allow RDS Proxy
resource "aws_security_group_rule" "aurora_from_proxy" {
  type                     = "ingress"
  from_port                = 3306
  to_port                  = 3306
  protocol                 = "tcp"
  security_group_id        = aws_security_group.aurora.id
  source_security_group_id = aws_security_group.rds_proxy.id
  description              = "MySQL from RDS Proxy"
}

###############################################################################
# IAM Role for RDS Proxy
###############################################################################

resource "aws_iam_role" "rds_proxy" {
  name = "${var.project_name}-rds-proxy-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "rds.amazonaws.com"
      }
    }]
  })

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-rds-proxy-role"
    App       = "shared"
    Component = "iam-role"
  })
}

resource "aws_iam_role_policy" "rds_proxy_secrets" {
  name = "${var.project_name}-rds-proxy-secrets-${var.environment}"
  role = aws_iam_role.rds_proxy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = aws_secretsmanager_secret.aurora_credentials.arn
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "secretsmanager.${var.aws_region}.amazonaws.com"
          }
        }
      }
    ]
  })
}

###############################################################################
# Outputs
###############################################################################

output "rds_proxy_endpoint" {
  description = "RDS Proxy endpoint - use this as AURORA_HOST for connection pooling"
  value       = aws_db_proxy.aurora.endpoint
}

output "rds_proxy_arn" {
  description = "RDS Proxy ARN"
  value       = aws_db_proxy.aurora.arn
}

output "rds_proxy_security_group_id" {
  description = "Security group ID for RDS Proxy"
  value       = aws_security_group.rds_proxy.id
}
