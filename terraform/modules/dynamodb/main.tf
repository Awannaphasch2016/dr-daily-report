# DynamoDB Module - Main Resources
# Flexible DynamoDB table with optional range key and GSIs

locals {
  full_table_name = "${var.project_name}-${var.table_name}-${var.environment}"

  # Build attributes list dynamically
  key_attributes = concat(
    [{ name = var.hash_key, type = var.hash_key_type }],
    var.range_key != null ? [{ name = var.range_key, type = var.range_key_type }] : []
  )

  # Get unique GSI attributes (only those not already in key schema)
  gsi_hash_keys  = [for gsi in var.global_secondary_indexes : gsi.hash_key if gsi.hash_key != var.hash_key && (var.range_key == null || gsi.hash_key != var.range_key)]
  gsi_range_keys = [for gsi in var.global_secondary_indexes : gsi.range_key if gsi.range_key != null && gsi.range_key != var.hash_key && (var.range_key == null || gsi.range_key != var.range_key)]

  # Merge tags
  resource_tags = merge(var.common_tags, {
    Name      = local.full_table_name
    App       = var.app_tag
    Component = var.component_tag
    DataType  = var.data_type_tag
  })
}

#------------------------------------------------------------------------------
# DynamoDB Table
#------------------------------------------------------------------------------

resource "aws_dynamodb_table" "this" {
  name         = local.full_table_name
  billing_mode = var.billing_mode

  # Provisioned capacity (only used if billing_mode = PROVISIONED)
  read_capacity  = var.billing_mode == "PROVISIONED" ? var.read_capacity : null
  write_capacity = var.billing_mode == "PROVISIONED" ? var.write_capacity : null

  # Key schema
  hash_key  = var.hash_key
  range_key = var.range_key

  # Hash key attribute
  attribute {
    name = var.hash_key
    type = var.hash_key_type
  }

  # Range key attribute (optional)
  dynamic "attribute" {
    for_each = var.range_key != null ? [1] : []
    content {
      name = var.range_key
      type = var.range_key_type
    }
  }

  # GSI hash key attributes (only add if not already defined)
  dynamic "attribute" {
    for_each = toset(local.gsi_hash_keys)
    content {
      name = attribute.value
      type = "S" # Default to String for GSI keys
    }
  }

  # GSI range key attributes (only add if not already defined)
  dynamic "attribute" {
    for_each = toset(local.gsi_range_keys)
    content {
      name = attribute.value
      type = "S" # Default to String for GSI keys
    }
  }

  # TTL configuration
  ttl {
    attribute_name = var.ttl_attribute_name
    enabled        = var.ttl_enabled
  }

  # Global Secondary Indexes
  dynamic "global_secondary_index" {
    for_each = var.global_secondary_indexes
    content {
      name               = global_secondary_index.value.name
      hash_key           = global_secondary_index.value.hash_key
      range_key          = global_secondary_index.value.range_key
      projection_type    = global_secondary_index.value.projection_type
      non_key_attributes = global_secondary_index.value.projection_type == "INCLUDE" ? global_secondary_index.value.non_key_attributes : null
      read_capacity      = var.billing_mode == "PROVISIONED" ? global_secondary_index.value.read_capacity : null
      write_capacity     = var.billing_mode == "PROVISIONED" ? global_secondary_index.value.write_capacity : null
    }
  }

  tags = local.resource_tags
}
