output "ecr_repository_uri" {
  description = "URI do repositório ECR (imagem buildada pelo CodeBuild)"
  value       = aws_ecr_repository.agent_ecr.repository_url
}

output "codebuild_project_name" {
  description = "Nome do projeto CodeBuild para buildar e publicar a imagem"
  value       = aws_codebuild_project.agent_build.name
}