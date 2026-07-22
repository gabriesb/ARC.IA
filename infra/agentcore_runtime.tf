resource "awscc_bedrockagentcore_runtime" "agent_runtime" {

  agent_runtime_name = "geo_agent"
  description        = "AgentCore Runtime do ${var.project_name}"
  role_arn           = awscc_iam_role.agent_runtime_role.arn

  agent_runtime_artifact = {
    container_configuration = {
      container_uri = "${data.aws_ecr_repository.agent_ecr.repository_url}:latest"
    }
  }

  network_configuration = {
    network_mode = "PUBLIC"
  }

  environment_variables = {
    "LOG_LEVEL" = "INFO"
  }

  tags = {
    "Project" = var.project_name
  }
}
