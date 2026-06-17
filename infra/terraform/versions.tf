terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
  }

  # Remote state is mandatory for team workflows. Fill in your bucket/table and
  # run `terraform init`. Kept commented so `terraform validate` works offline.
  # backend "s3" {
  #   bucket         = "my-tfstate-bucket"
  #   key            = "microservices-fastapi-platform/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "microservices-fastapi-platform"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
