# Terraform S3 Backend Configuration - Staging Environment
# Used with: terraform init -backend-config=envs/staging/backend.hcl

bucket         = "dr-daily-report-tf-state"
key            = "telegram-api/staging/terraform.tfstate"
region         = "ap-southeast-1"
dynamodb_table = "dr-daily-report-tf-locks"
encrypt        = true
