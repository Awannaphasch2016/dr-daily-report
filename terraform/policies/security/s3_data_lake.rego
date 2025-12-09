# S3 Data Lake Security Policy
#
# Enforces S3 Data Lake best practices for raw data staging:
# - Versioning MUST be enabled (data lineage requirement)
# - Object tagging MUST be configured (metadata tracking)
# - Lifecycle policies SHOULD be configured (cost optimization)
# - Encryption at rest MUST be enabled
# - Public access MUST be blocked
#
# Usage: conftest test tfplan.json --policy policies/

package terraform.security.s3_data_lake

import future.keywords.in
import future.keywords.if
import future.keywords.contains

# Helper: Identify data lake buckets by name pattern
is_data_lake_bucket(bucket_name) if {
    contains(bucket_name, "data-lake")
}

is_data_lake_bucket(bucket_name) if {
    contains(bucket_name, "datalake")
}

is_data_lake_bucket(bucket_name) if {
    contains(bucket_name, "raw-data")
}

# Helper: Extract module path from resource address (handles both root and module resources)
module_path(address) = path if {
    # Extract everything before the last dot-separated resource type
    parts := split(address, ".")
    # For module resources: module.s3_data_lake.aws_s3_bucket.data_lake -> module.s3_data_lake
    # For root resources: aws_s3_bucket.data_lake -> ""
    count(parts) > 2
    parts[0] == "module"
    path := sprintf("%s.%s", [parts[0], parts[1]])
}

module_path(address) = "" if {
    # Root-level resource (no module prefix)
    parts := split(address, ".")
    parts[0] != "module"
}

# Helper: Check if bucket has versioning enabled (handles module resources)
has_versioning_enabled(bucket_address) if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket_versioning"
    bucket_module := module_path(bucket_address)
    versioning_module := module_path(resource.address)
    bucket_module == versioning_module
    resource.change.after.versioning_configuration[_].status == "Enabled"
}

# Fallback for root-level resources
has_versioning_enabled(bucket_address) if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket_versioning"
    bucket_module := module_path(bucket_address)
    bucket_module == ""
    # Extract bucket name from bucket address for root-level matching
    contains(resource.address, split(bucket_address, ".")[count(split(bucket_address, ".")) - 1])
    resource.change.after.versioning_configuration[_].status == "Enabled"
}

# Helper: Check if bucket has lifecycle policy configured (handles module resources)
has_lifecycle_policy(bucket_address) if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket_lifecycle_configuration"
    bucket_module := module_path(bucket_address)
    lifecycle_module := module_path(resource.address)
    bucket_module == lifecycle_module
}

# Helper: Check if bucket has object tagging configured (via Lambda or default tags)
has_tagging_strategy(bucket_name) if {
    # Check if Lambda has S3 write permissions (implies tagging will happen)
    resource := input.resource_changes[_]
    resource.type == "aws_iam_policy"
    contains(resource.change.after.policy, "s3:PutObjectTagging")
}

# DENY: Data lake buckets MUST have versioning enabled
deny contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket"
    resource.change.actions[_] == "create"
    bucket_name := resource.change.after.bucket
    is_data_lake_bucket(bucket_name)
    not has_versioning_enabled(resource.address)
    msg := sprintf("Data lake bucket '%s' MUST enable versioning for data lineage and reproducibility. Add aws_s3_bucket_versioning with status='Enabled'.", [resource.address])
}

# WARN: Data lake buckets SHOULD have lifecycle policies for cost optimization
warn contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket"
    resource.change.actions[_] == "create"
    bucket_name := resource.change.after.bucket
    is_data_lake_bucket(bucket_name)
    not has_lifecycle_policy(resource.address)
    msg := sprintf("Data lake bucket '%s' should configure lifecycle policies to transition old data to Glacier (reduce costs). Recommended: 90 days Standard → 365 days Glacier → delete.", [resource.address])
}

# DENY: Data lake buckets storing raw API data MUST have encryption
deny contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket"
    resource.change.actions[_] == "create"
    bucket_name := resource.change.after.bucket
    is_data_lake_bucket(bucket_name)
    not has_server_side_encryption(resource.address)
    msg := sprintf("Data lake bucket '%s' MUST enable server-side encryption (SSE-S3 or SSE-KMS) to protect raw API data. Add aws_s3_bucket_server_side_encryption_configuration.", [resource.address])
}

# Helper: Check if bucket has server-side encryption (handles module resources)
has_server_side_encryption(bucket_address) if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket_server_side_encryption_configuration"
    bucket_module := module_path(bucket_address)
    encryption_module := module_path(resource.address)
    bucket_module == encryption_module
}

# DENY: Data lake buckets MUST block public access
deny contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket"
    resource.change.actions[_] == "create"
    bucket_name := resource.change.after.bucket
    is_data_lake_bucket(bucket_name)
    not has_public_access_block(resource.address)
    msg := sprintf("Data lake bucket '%s' MUST block all public access. Raw data should never be publicly accessible. Add aws_s3_bucket_public_access_block with all settings = true.", [resource.address])
}

# Helper: Check if bucket has public access block (handles module resources)
has_public_access_block(bucket_address) if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket_public_access_block"
    bucket_module := module_path(bucket_address)
    pab_module := module_path(resource.address)
    bucket_module == pab_module
    resource.change.after.block_public_acls == true
    resource.change.after.block_public_policy == true
    resource.change.after.ignore_public_acls == true
    resource.change.after.restrict_public_buckets == true
}

# WARN: Data lake buckets should follow naming convention
warn contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket"
    resource.change.actions[_] == "create"
    bucket_name := resource.change.after.bucket
    is_data_lake_bucket(bucket_name)
    # Check naming pattern: {app}-data-lake-{env}
    not contains(bucket_name, "-dev")
    not contains(bucket_name, "-staging")
    not contains(bucket_name, "-prod")
    msg := sprintf("Data lake bucket '%s' should include environment suffix (-dev, -staging, -prod) for clarity. Example: dr-daily-report-data-lake-dev", [bucket_name])
}

# DENY: Data lake buckets MUST have required tags (for cost tracking and lineage)
deny contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket"
    resource.change.actions[_] == "create"
    bucket_name := resource.change.after.bucket
    is_data_lake_bucket(bucket_name)
    tags := resource.change.after.tags
    not tags["Purpose"]
    msg := sprintf("Data lake bucket '%s' MUST have 'Purpose' tag (e.g., 'raw-data-staging', 'processed-data'). Required for cost tracking and data lineage.", [resource.address])
}

deny contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket"
    resource.change.actions[_] == "create"
    bucket_name := resource.change.after.bucket
    is_data_lake_bucket(bucket_name)
    tags := resource.change.after.tags
    not tags["DataClassification"]
    msg := sprintf("Data lake bucket '%s' MUST have 'DataClassification' tag (e.g., 'public-api-data', 'internal'). Required for security compliance.", [resource.address])
}
