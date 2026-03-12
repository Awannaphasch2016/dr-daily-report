# Terraform S3 Backend Configuration - Feature-Alerts Environment
# Used with: terraform init -backend-config=envs/feature-alerts/backend.hcl
#
# Cleanup:
#   1. terraform destroy -var-file=terraform.feature-alerts.tfvars
#   2. aws s3 rm s3://dr-daily-report-tf-state/telegram-api/feature-alerts/ --recursive
#   3. rm -rf envs/feature-alerts

bucket         = "dr-daily-report-tf-state"
key            = "telegram-api/feature-alerts/terraform.tfstate"
region         = "ap-southeast-1"
dynamodb_table = "dr-daily-report-tf-locks"
encrypt        = true
