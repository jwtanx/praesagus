// Terraform scaffold for Praesagus (example and placeholder values)
terraform {
  required_version = ">= 1.0"
}

provider "aws" {
  region = var.aws_region
}

resource "aws_s3_bucket" "raw_data" {
  bucket = "praesagus-raw-data-example-${var.env}"
  acl    = "private"

  tags = {
    Name = "praesagus-raw-data"
    Env  = var.env
  }
}

resource "aws_s3_bucket" "bronze_data" {
  bucket = "praesagus-bronze-data-example-${var.env}"
  acl    = "private"

  tags = {
    Name = "praesagus-bronze-data"
    Env  = var.env
  }
}

resource "aws_s3_bucket" "silver_data" {
  bucket = "praesagus-silver-data-example-${var.env}"
  acl    = "private"

  tags = {
    Name = "praesagus-silver-data"
    Env  = var.env
  }
}

output "raw_bucket" {
  value = aws_s3_bucket.raw_data.id
}

output "bronze_bucket" {
  value = aws_s3_bucket.bronze_data.id
}

output "silver_bucket" {
  value = aws_s3_bucket.silver_data.id
}

resource "aws_dynamodb_table" "feature_store" {
  name         = "praesagus-feature-store-${var.env}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "entity"

  attribute {
    name = "entity"
    type = "S"
  }

  tags = {
    Name = "praesagus-feature-store"
    Env  = var.env
  }
}

resource "aws_secretsmanager_secret" "connector_credentials" {
  name        = "praesagus-connector-credentials-${var.env}"
  description = "Connector credentials and API keys for Praesagus ingestion tasks"
  tags = {
    Name = "praesagus-connector-credentials"
    Env  = var.env
  }
}

resource "aws_secretsmanager_secret_version" "connector_credentials_version" {
  secret_id     = aws_secretsmanager_secret.connector_credentials.id
  secret_string = jsonencode({
    reddit_client_id     = "",
    reddit_client_secret = "",
    twitter_bearer_token = "",
  })
}

resource "aws_sqs_queue" "ingest_dlq" {
  name                        = "praesagus-ingest-dlq-${var.env}"
  visibility_timeout_seconds  = 300
  message_retention_seconds   = 1209600
  delay_seconds               = 0
  receive_wait_time_seconds   = 0
}

output "feature_table" {
  value = aws_dynamodb_table.feature_store.name
}
