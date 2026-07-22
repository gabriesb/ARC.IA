# OIDC Provider do GitHub Actions já existe na conta — apenas referenciamos
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

# IAM Role assumida pelo GitHub Actions via OIDC
resource "aws_iam_role" "github_actions_ecr_role" {
  name = "github-actions-ecr"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = data.aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          # Restringe à branch configurada em var.build_branch
          "token.actions.githubusercontent.com:sub" = "repo:gabriesb/AgentCore-Easy-Deploy:ref:refs/heads/${var.build_branch}"
        }
      }
    }]
  })
}

# Permissões para login e push no ECR
resource "aws_iam_role_policy" "github_actions_ecr_policy" {
  name = "github-actions-ecr-policy"
  role = aws_iam_role.github_actions_ecr_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
        Resource = aws_ecr_repository.agent_ecr.arn
      }
    ]
  })
}
