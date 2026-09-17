resource "awscc_bedrockagentcore_runtime" "agent_runtime" {

  agent_runtime_name = "agent_runtime"
  description        = "AgentCore Runtime do ${var.project_name}"
  role_arn           = awscc_iam_role.agent_runtime_role.arn

  agent_runtime_artifact = {
    container_configuration = {
      container_uri = "${data.aws_ecr_repository.agent_ecr.repository_url}:${var.image_tag}"
    }
  }

  network_configuration = {
    network_mode = "PUBLIC"
  }

  environment_variables = {
    "LOG_LEVEL"               = "INFO"
    "GITHUB_TOKEN_SECRET_ARN" = data.aws_secretsmanager_secret.github_token.arn
    "DIAGRAM_BUCKET_NAME"     = data.aws_s3_bucket.diagrams.bucket
  }

  tags = {
    "Project" = var.project_name
  }

  depends_on = [awscc_iam_role_policy.agent_runtime_policy]
}
