resource "aws_s3_bucket" "example" {
  bucket = "agent-runtime-state"

  force_destroy = true

  tags = {
    Name        = "agent-state"
    Environment = "Dev"
  }
}