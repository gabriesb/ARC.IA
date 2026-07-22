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
          # Permite qualquer branch/ref do repositório
          "token.actions.githubusercontent.com:sub" = "repo:gabriesb/AgentCore-Easy-Deploy:*"
        }
      }
    }]
  })
}

# Permissões para login e push no ECR + terraform apply na /infra
resource "aws_iam_role_policy" "github_actions_ecr_policy" {
  name = "github-actions-ecr-policy"
  role = aws_iam_role.github_actions_ecr_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # ECR login
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        # ECR push/pull
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
        Resource = "*"
      },
      {
        # S3 — backend do Terraform state
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::agent-state",
          "arn:aws:s3:::agent-state/*"
        ]
      },
      {
        # IAM — criação/atualização de roles e policies pelo Terraform
        Effect = "Allow"
        Action = [
          "iam:GetRole",
          "iam:CreateRole",
          "iam:UpdateRole",
          "iam:DeleteRole",
          "iam:PutRolePolicy",
          "iam:GetRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy",
          "iam:PassRole",
          "iam:ListRolePolicies",
          "iam:ListAttachedRolePolicies",
          "iam:TagRole",
          "iam:UntagRole"
        ]
        Resource = "*"
      },
      {
        # BedrockAgentCore — criar/atualizar o runtime via awscc
        Effect = "Allow"
        Action = [
          "bedrock:*",
          "bedrock-agentcore:*",
          "bedrock-agentcore-control:*"
        ]
        Resource = "*"
      },
      {
        # CloudControl API — usada pelo provider awscc
        Effect   = "Allow"
        Action   = "cloudformation:*"
        Resource = "*"
      },
      {
        # Leitura de recursos gerais necessários ao Terraform
        Effect = "Allow"
        Action = [
          "sts:GetCallerIdentity",
          "ec2:DescribeRegions",
          "logs:CreateLogGroup",
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      }
    ]
  })
}
