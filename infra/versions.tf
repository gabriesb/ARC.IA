terraform {
  backend "s3" {
      bucket = "agent-runtime-state"
      key    = "terraform.tfstate"
      region = "us-east-1"
    }
  required_providers {
    aws = { 
        source = "hashicorp/aws"
        version = "~>5.0"
    }

    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }

    awscc = { 
        source = "hashicorp/awscc"
        version = "1.86.0"
    }
  }
}