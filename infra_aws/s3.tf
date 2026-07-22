resource "aws_s3_bucket" "example" {
  bucket = "agent-runtime-state"

  tags = {
    Name        = "agent-state"
    Environment = "Dev"
  }
}