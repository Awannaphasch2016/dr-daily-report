# S3 Event Notification for Fund Data CSV Uploads
#
# Purpose: Trigger Fund Data Sync ETL pipeline when CSV files are uploaded
# Flow: CSV uploaded to S3 → Event notification → SQS → Lambda → Aurora
#
# Event Filter:
#   Prefix: raw/sql_server/fund_data/
#   Suffix: .csv
#
# Design Principles:
# - Event-driven: No polling, immediate processing on upload
# - Prefix/suffix filtering: Only CSV files in correct path trigger pipeline
# - SQS buffering: Decouples S3 events from Lambda processing

# ============================================================================
# S3 Bucket Notification Configuration
# ============================================================================

resource "aws_s3_bucket_notification" "fund_data_csv_upload" {
  bucket = module.s3_data_lake.bucket_id

  # SQS Queue Destination
  queue {
    id            = "fund-data-csv-upload"
    queue_arn     = module.fund_data_sync_queue.queue_arn
    events        = ["s3:ObjectCreated:*"]  # All ObjectCreated events (Put, Post, Copy, CompleteMultipartUpload)

    # Filter: Only CSV files in fund_data directory
    filter_prefix = "raw/sql_server/fund_data/"
    filter_suffix = ".csv"
  }

  depends_on = [
    module.fund_data_sync_queue,
    aws_sqs_queue_policy.allow_s3_send_to_fund_data_queue
  ]
}

# ============================================================================
# SQS Queue Policy: Allow S3 to Send Messages
# ============================================================================

# Allow S3 bucket to send messages to SQS queue
resource "aws_sqs_queue_policy" "allow_s3_send_to_fund_data_queue" {
  queue_url = module.fund_data_sync_queue.queue_url

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowS3ToSendMessage"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = module.fund_data_sync_queue.queue_arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = module.s3_data_lake.bucket_arn
          }
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

# ============================================================================
# Outputs
# ============================================================================

output "s3_event_notification_id" {
  description = "ID of S3 event notification for fund data CSV uploads"
  value       = aws_s3_bucket_notification.fund_data_csv_upload.id
}
