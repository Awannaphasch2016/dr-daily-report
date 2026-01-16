# Static API Infrastructure - S3 + CloudFront
#
# Purpose: Serve pre-computed JSON data for high-read performance
# Architecture:
#   - S3 bucket stores static JSON files (rankings, reports, patterns)
#   - CloudFront CDN provides edge caching (global low latency)
#   - Precompute workflow generates and uploads JSON nightly
#
# Performance Target:
#   - TTFB < 50ms (from CloudFront edge)
#   - Cache hit ratio > 95%
#   - Zero Aurora load for reads
#
# Cost Estimate:
#   - S3: ~$0.023/GB/month (minimal for JSON)
#   - CloudFront: ~$0.085/GB (first 10TB)
#   - Estimated: < $5/month for demo traffic

###############################################################################
# Variables
###############################################################################

variable "static_api_cache_ttl" {
  description = "Default TTL for static API CloudFront cache (seconds)"
  type        = number
  default     = 86400  # 24 hours - data refreshed nightly
}

variable "static_api_enabled" {
  description = "Whether to create static API infrastructure"
  type        = bool
  default     = true
}

###############################################################################
# S3 Bucket for Static API
###############################################################################

resource "aws_s3_bucket" "static_api" {
  count  = var.static_api_enabled ? 1 : 0
  bucket = "${var.project_name}-static-api-${var.environment}"

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-static-api"
    App       = "shared"
    Component = "static-api-storage"
  })
}

resource "aws_s3_bucket_versioning" "static_api" {
  count  = var.static_api_enabled ? 1 : 0
  bucket = aws_s3_bucket.static_api[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "static_api" {
  count  = var.static_api_enabled ? 1 : 0
  bucket = aws_s3_bucket.static_api[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access - only CloudFront can access
resource "aws_s3_bucket_public_access_block" "static_api" {
  count  = var.static_api_enabled ? 1 : 0
  bucket = aws_s3_bucket.static_api[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

###############################################################################
# CloudFront Origin Access Control (OAC) - Modern approach
###############################################################################

resource "aws_cloudfront_origin_access_control" "static_api" {
  count                             = var.static_api_enabled ? 1 : 0
  name                              = "${var.project_name}-static-api-oac-${var.environment}"
  description                       = "OAC for Static API S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

###############################################################################
# S3 Bucket Policy - Allow CloudFront OAC access
###############################################################################

resource "aws_s3_bucket_policy" "static_api" {
  count  = var.static_api_enabled ? 1 : 0
  bucket = aws_s3_bucket.static_api[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipal"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.static_api[0].arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.static_api[0].arn
          }
        }
      }
    ]
  })
}

###############################################################################
# CloudFront Distribution for Static API
###############################################################################

resource "aws_cloudfront_distribution" "static_api" {
  count = var.static_api_enabled ? 1 : 0

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "Static API CDN for ${var.project_name} (${var.environment})"
  default_root_object = "api/v1/rankings.json"
  price_class         = "PriceClass_200"  # US, Canada, Europe, Asia, Middle East, Africa

  origin {
    domain_name              = aws_s3_bucket.static_api[0].bucket_regional_domain_name
    origin_id                = "S3-static-api"
    origin_access_control_id = aws_cloudfront_origin_access_control.static_api[0].id
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-static-api"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = var.static_api_cache_ttl
    max_ttl                = var.static_api_cache_ttl * 2
    compress               = true

    # CORS headers for cross-origin requests from webapp
    response_headers_policy_id = aws_cloudfront_response_headers_policy.static_api_cors[0].id
  }

  # Custom error response - return empty JSON for missing files
  custom_error_response {
    error_code            = 404
    response_code         = 404
    response_page_path    = "/api/v1/error/not-found.json"
    error_caching_min_ttl = 60
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-static-api-cdn"
    App       = "shared"
    Component = "static-api-cdn"
  })
}

###############################################################################
# CloudFront Response Headers Policy - CORS for API
###############################################################################

resource "aws_cloudfront_response_headers_policy" "static_api_cors" {
  count = var.static_api_enabled ? 1 : 0
  name  = "${var.project_name}-static-api-cors-${var.environment}"

  cors_config {
    access_control_allow_credentials = false

    access_control_allow_headers {
      items = ["*"]
    }

    access_control_allow_methods {
      items = ["GET", "HEAD", "OPTIONS"]
    }

    access_control_allow_origins {
      items = [
        "https://*.cloudfront.net",
        "http://localhost:*",
        "https://localhost:*",
        "https://web.telegram.org",
        "https://*.telegram.org"
      ]
    }

    access_control_max_age_sec = 86400
    origin_override            = true
  }

  custom_headers_config {
    items {
      header   = "Cache-Control"
      value    = "public, max-age=${var.static_api_cache_ttl}"
      override = false
    }
  }
}

###############################################################################
# IAM Policy for Lambda to upload to Static API bucket
###############################################################################

resource "aws_iam_policy" "lambda_static_api_upload" {
  count       = var.static_api_enabled ? 1 : 0
  name        = "${var.project_name}-lambda-static-api-upload-${var.environment}"
  description = "Allow Lambda to upload static API JSON files to S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.static_api[0].arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.static_api[0].arn
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-lambda-static-api-policy"
    App       = "shared"
    Component = "iam-policy"
  })
}

###############################################################################
# Outputs
###############################################################################

output "static_api_bucket_name" {
  description = "S3 bucket name for static API"
  value       = var.static_api_enabled ? aws_s3_bucket.static_api[0].id : null
}

output "static_api_bucket_arn" {
  description = "S3 bucket ARN for static API"
  value       = var.static_api_enabled ? aws_s3_bucket.static_api[0].arn : null
}

output "static_api_cloudfront_domain" {
  description = "CloudFront domain name for static API"
  value       = var.static_api_enabled ? aws_cloudfront_distribution.static_api[0].domain_name : null
}

output "static_api_cloudfront_distribution_id" {
  description = "CloudFront distribution ID for static API"
  value       = var.static_api_enabled ? aws_cloudfront_distribution.static_api[0].id : null
}

output "static_api_url" {
  description = "Full URL for static API (use this in frontend)"
  value       = var.static_api_enabled ? "https://${aws_cloudfront_distribution.static_api[0].domain_name}" : null
}

output "lambda_static_api_upload_policy_arn" {
  description = "IAM policy ARN for Lambda to upload static API files"
  value       = var.static_api_enabled ? aws_iam_policy.lambda_static_api_upload[0].arn : null
}
