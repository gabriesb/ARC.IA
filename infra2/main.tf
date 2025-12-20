resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  suffix       = random_id.suffix.hex
  runtime_name = "agentcore_math_pro_${local.suffix}"
  role_name    = "bedrock-agent-runtime-role-${local.suffix}"

  # Imagem do math-pro (ajuste se usar outro repo/tag)
  ecr_image = "841162693674.dkr.ecr.us-west-2.amazonaws.com/bedrock/agent-runtime-math:latest"
}

# =========================================================
# IAM Role (assumida pelo AgentCore Runtime)
# =========================================================
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

# =========================================================
# Policy do runtime
# =========================================================
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

# =========================================================
# AgentCore Runtime — math-pro
# =========================================================
resource "awscc_bedrockagentcore_runtime" "math_pro" {
  agent_runtime_name = "agentcore_math_pro_${random_id.suffix.hex}"
  description        = "Agent Core Runtime for Math-Pro (Mathematics Specialist)"
  role_arn           = awscc_iam_role.agent_runtime_role.arn

  agent_runtime_artifact = {
    container_configuration = {
      container_uri = "841162693674.dkr.ecr.us-west-2.amazonaws.com/bedrock/agent-runtime-math:latest"
    }
  }

  network_configuration = {
    network_mode = "PUBLIC"
  }

  environment_variables = {
    LOG_LEVEL = "INFO"
  }

  tags = {
    Runtime    = "math-pro"
    CostCenter = "agentcore"
    Project    = "agents"
    Domain     = "mathematics"
    Env        = "dev"
  }
}
