terraform {
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
        version = "<=1.8.6"
    }
  }
}