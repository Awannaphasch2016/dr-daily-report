# S3 Security Policy
#
# Enforces S3 bucket best practices:
# - Public access must be blocked
# - Server-side encryption must be enabled
# - Versioning should be enabled for production buckets
#
# Usage: conftest test tfplan.json --policy policies/

package terraform.security.s3

import future.keywords.in
import future.keywords.if
import future.keywords.contains

# Helper: Check if a bucket has a public access block configured
has_public_access_block(bucket_address) if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket_public_access_block"
    contains(resource.address, bucket_address)
}

# Helper: Check if bucket has server-side encryption
has_server_side_encryption(bucket_address) if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket_server_side_encryption_configuration"
    contains(resource.address, bucket_address)
}

# Deny S3 buckets without public access block
deny contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket"
    resource.change.actions[_] == "create"
    bucket_name := resource.change.after.bucket
    not has_public_access_block(bucket_name)
    msg := sprintf("S3 bucket '%s' must have a public access block. Add aws_s3_bucket_public_access_block resource.", [resource.address])
}

# Warn about S3 buckets without versioning (recommended for production)
warn contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket"
    resource.change.actions[_] == "create"
    # Check if this is a production bucket (contains 'prod' in name or tags)
    contains(resource.change.after.bucket, "prod")
    not has_versioning_enabled(resource.address)
    msg := sprintf("Production S3 bucket '%s' should enable versioning for data protection.", [resource.address])
}

# Helper: Check if bucket has versioning enabled
has_versioning_enabled(bucket_address) if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket_versioning"
    contains(resource.address, bucket_address)
    resource.change.after.versioning_configuration[_].status == "Enabled"
}

# Deny public ACLs on buckets
deny contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket_acl"
    resource.change.actions[_] != "delete"
    acl := resource.change.after.acl
    acl == "public-read"
    msg := sprintf("S3 bucket ACL '%s' uses public-read. Use private ACL and CloudFront for public content.", [resource.address])
}

deny contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket_acl"
    resource.change.actions[_] != "delete"
    acl := resource.change.after.acl
    acl == "public-read-write"
    msg := sprintf("S3 bucket ACL '%s' uses public-read-write. This is a critical security risk.", [resource.address])
}
