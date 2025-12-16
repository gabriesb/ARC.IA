resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  suffix      = random_id.suffix.hex
  runtime_name = "${var.project_name}-${local.suffix}"
  role_name    = "bedrock-agent-runtime-role-${local.suffix}"
  ecr_name     = "bedrock/agent-runtime-${local.suffix}"
}

resource "awscc_ecr_repository" "agent_runtime" {
  repository_name = local.ecr_name

  tags = [{
    key   = "Modified By"
    value = "AWSCC"
  }]
}

# IAM Role (assumida pelo AgentCore Runtime)
resource "awscc_iam_role" "agent_runtime_role" {
  role_name = local.role_name

  assume_role_policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "bedrock-agentcore.amazonaws.com"
      }
    }]
  })

  tags = [{
    key   = "Modified By"
    value = "AWSCC"
  }]
}

# Policy do runtime:
# - InvokeModel (pra chamar o Bedrock)
# - Logs (CloudWatch)
# - ECR pull (runtime puxar a imagem)
resource "awscc_iam_role_policy" "agent_runtime_policy" {
  role_name   = awscc_iam_role.agent_runtime_role.role_name
  policy_name = "bedrock-agent-runtime-policy"

  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
        Resource = "*"
      }
    ]
  })
}


# AgentCore Runtime (container)
resource "awscc_bedrockagentcore_runtime" "runtime" {
  agent_runtime_name = "agentcore_geopro_tutor_${random_id.suffix.hex}"
  description        = "Agent Core Runtime for GeoPro Tutor"
  role_arn           = awscc_iam_role.agent_runtime_role.arn

  agent_runtime_artifact = {
    container_configuration = {
      container_uri = "${awscc_ecr_repository.agent_runtime.repository_uri}:latest"
    }
  }

  network_configuration = {
    network_mode = "PUBLIC"
  }

  environment_variables = {
    LOG_LEVEL = "INFO"
  }

  tags = {
    Environment = "dev"
    Project     = "agentcore"
  }
}

#resource "awscc_bedrockagentcore_gateway" "agent" {
#  gateway_name = "agentcore_gateway_${random_id.suffix.hex}"
#  description  = "Gateway for Agent Core Runtime"
#  role_arn     = awscc_iam_role.agent_runtime_role.arn
#
#  network_configuration = {
#    network_mode = "PUBLIC"
#  }
#}