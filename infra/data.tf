data "aws_caller_identity" "current" {}

data "aws_ecr_repository" "agent_ecr" {
  name = "agent_ecr"
}

# Recursos criados no bootstrap (infra_aws/) e apenas referenciados aqui.
data "aws_s3_bucket" "diagrams" {
  bucket = "agent-diagrams-${data.aws_caller_identity.current.account_id}"
}

data "aws_secretsmanager_secret" "github_token" {
  name = "agentcore-easy-deploy/github-token"
}