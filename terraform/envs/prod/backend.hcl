# Terraform S3 Backend Configuration - Production Environment
# Used with: terraform init -backend-config=envs/prod/backend.hcl

bucket         = "dr-daily-report-tf-state"
key            = "telegram-api/prod/terraform.tfstate"
region         = "ap-southeast-1"
dynamodb_table = "dr-daily-report-tf-locks"
encrypt        = true
