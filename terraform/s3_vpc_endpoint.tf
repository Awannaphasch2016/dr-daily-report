###############################################################################
# S3 VPC Gateway Endpoint
#
# Resolves: PDF worker S3 upload connection timeouts (50% failure rate)
# Root Cause: NAT Gateway connection saturation with concurrent Lambda uploads
# Solution: Gateway endpoint keeps S3 traffic within AWS network (no NAT)
#
# Benefits:
# - FREE (Gateway endpoints have no hourly charge)
# - Faster (direct AWS network path, no NAT hop)
# - Reliable (no NAT connection limits)
# - Secure (traffic never leaves AWS network)
###############################################################################

# Get all route tables in the VPC
data "aws_route_tables" "vpc_route_tables" {
  vpc_id = data.aws_vpc.default.id
}

# S3 Gateway Endpoint (attaches to route tables)
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"

  # Attach to all route tables in the VPC
  # This ensures all subnets (including Lambda subnets) can reach S3
  route_table_ids = data.aws_route_tables.vpc_route_tables.ids

  # Policy: Allow full S3 access (can be restricted if needed)
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:*"
        Resource  = "*"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-s3-endpoint-${var.environment}"
    Component = "networking"
    Purpose   = "PDF S3 upload reliability"
  })
}

# Output for verification
output "s3_vpc_endpoint_id" {
  description = "S3 VPC Endpoint ID"
  value       = aws_vpc_endpoint.s3.id
}

output "s3_vpc_endpoint_state" {
  description = "S3 VPC Endpoint state"
  value       = aws_vpc_endpoint.s3.state
}
