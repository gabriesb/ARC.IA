data "aws_caller_identity" "current" {}

# S3 bucket to store generated .drawio architecture diagrams (used to hand
# back a presigned download URL instead of always inlining the XML). Lives in
# the bootstrap module because it is a long-lived resource created once, not
# something that should be re-created alongside the agent runtime.
resource "aws_s3_bucket" "diagrams" {
  bucket        = "agent-diagrams-${data.aws_caller_identity.current.account_id}"
  force_destroy = true

  tags = {
    Name = "agent-diagrams"
  }
}

resource "aws_s3_bucket_public_access_block" "diagrams" {
  bucket = aws_s3_bucket.diagrams.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Secrets Manager container for the GitHub Personal Access Token used to read
# repositories (Terraform code) that the agent turns into architecture
# diagrams. Only the secret *container* is created here — populate the value
# out-of-band (e.g. `aws secretsmanager put-secret-value`) so the token never
# goes through Terraform state.
resource "aws_secretsmanager_secret" "github_token" {
  name                    = "agentcore-easy-deploy/github-token"
  description             = "GitHub PAT used by the agent to read repositories for architecture diagram generation."
  recovery_window_in_days = 0

  tags = {
    Name = "agent-github-token"
  }
}
