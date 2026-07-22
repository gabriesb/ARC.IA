resource "aws_codebuild_project" "agent_build" {
  name          = "${var.project_name}-build-${local.suffix}"
  description   = "Builda a imagem Docker do agent e faz push para o ECR"
  build_timeout  = 20
  service_role   = aws_iam_role.codebuild_role.arn
  source_version = var.build_branch

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/standard:7.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true # necessário para rodar Docker

    environment_variable {
      name  = "ECR_REPO_URI"
      value = aws_ecr_repository.agent_ecr.repository_url
    }

    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = data.aws_caller_identity.current.account_id
    }
  }

  source {
    type            = "GITHUB"
    location        = "https://github.com/gabriesb/AgentCore-Easy-Deploy"
    git_clone_depth = 1

    buildspec = <<-BUILDSPEC
      version: 0.2
      phases:
        pre_build:
          commands:
            - echo "Fazendo login no ECR..."
            - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $ECR_REPO_URI
        build:
          commands:
            - echo "Buildando imagem Docker..."
            - docker build -t $ECR_REPO_URI:latest src/
        post_build:
          commands:
            - echo "Fazendo push para o ECR..."
            - docker push $ECR_REPO_URI:latest
            - echo "Build concluído. Imagem disponível em $ECR_REPO_URI:latest"
    BUILDSPEC
  }

  logs_config {
    cloudwatch_logs {
      group_name  = "/codebuild/${var.project_name}-build"
      stream_name = "build-log"
    }
  }
}

data "aws_caller_identity" "current" {}
