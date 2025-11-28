# Frontend Infrastructure for Telegram Mini App
# S3 bucket for static files + CloudFront CDN for global distribution

###############################################################################
# S3 Bucket for WebApp Static Files
###############################################################################

resource "aws_s3_bucket" "webapp" {
  bucket = "${var.project_name}-webapp-${var.environment}"

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-webapp-${var.environment}"
    App       = "telegram-api"
    Component = "frontend-storage"
  })
}

# Block all public access - CloudFront will access via OAI
resource "aws_s3_bucket_public_access_block" "webapp" {
  bucket = aws_s3_bucket.webapp.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Bucket policy - only allow CloudFront OAI to read
resource "aws_s3_bucket_policy" "webapp" {
  bucket = aws_s3_bucket.webapp.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontOAI"
        Effect    = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.webapp.iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.webapp.arn}/*"
      }
    ]
  })
}

###############################################################################
# CloudFront Origin Access Identity
###############################################################################

resource "aws_cloudfront_origin_access_identity" "webapp" {
  comment = "OAI for ${var.project_name} Telegram WebApp"
}

###############################################################################
# CloudFront Distribution
###############################################################################

resource "aws_cloudfront_distribution" "webapp" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  comment             = "Telegram Mini App - ${var.environment}"
  price_class         = "PriceClass_200" # US, Canada, Europe, Asia (excludes expensive regions)

  origin {
    domain_name = aws_s3_bucket.webapp.bucket_regional_domain_name
    origin_id   = "S3-webapp"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.webapp.cloudfront_access_identity_path
    }
  }

  # Default cache behavior for static assets
  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-webapp"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600      # 1 hour
    max_ttl                = 86400     # 24 hours
    compress               = true
  }

  # Cache behavior for HTML files (shorter TTL for updates)
  ordered_cache_behavior {
    path_pattern     = "*.html"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-webapp"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 300       # 5 minutes
    max_ttl                = 3600      # 1 hour
    compress               = true
  }

  # Cache behavior for JS/CSS (longer TTL, use versioning)
  ordered_cache_behavior {
    path_pattern     = "*.js"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-webapp"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 86400     # 24 hours
    max_ttl                = 604800    # 7 days
    compress               = true
  }

  ordered_cache_behavior {
    path_pattern     = "*.css"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-webapp"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 86400     # 24 hours
    max_ttl                = 604800    # 7 days
    compress               = true
  }

  # SPA routing: return index.html for 404s (client-side routing)
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
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
    Name      = "${var.project_name}-webapp-cloudfront-${var.environment}"
    App       = "telegram-api"
    Component = "frontend-cdn"
  })
}

###############################################################################
# Outputs
###############################################################################

output "webapp_bucket_name" {
  value       = aws_s3_bucket.webapp.id
  description = "Name of the S3 bucket for webapp files"
}

output "webapp_bucket_arn" {
  value       = aws_s3_bucket.webapp.arn
  description = "ARN of the S3 bucket for webapp files"
}

output "cloudfront_distribution_id" {
  value       = aws_cloudfront_distribution.webapp.id
  description = "ID of the CloudFront distribution (needed for cache invalidation)"
}

output "cloudfront_distribution_domain" {
  value       = aws_cloudfront_distribution.webapp.domain_name
  description = "CloudFront domain name for the webapp"
}

output "webapp_url" {
  value       = "https://${aws_cloudfront_distribution.webapp.domain_name}"
  description = "Full URL for the Telegram Mini App"
}
