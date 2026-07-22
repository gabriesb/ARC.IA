data "aws_caller_identity" "current" {}

data "aws_ecr_repository" "agent_ecr" {
  name = "agent_ecr"
}