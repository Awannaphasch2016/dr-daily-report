# Terraform S3 Backend Configuration - Dev Environment
# Used with: terraform init -backend-config=envs/dev/backend.hcl

bucket         = "dr-daily-report-tf-state"
key            = "telegram-api/dev/terraform.tfstate"
region         = "ap-southeast-1"
dynamodb_table = "dr-daily-report-tf-locks"
encrypt        = true
