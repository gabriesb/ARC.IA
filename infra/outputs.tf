output "ecr_repository_uri" {
  description = "URI do repositório ECR"
  value       = aws_ecr_repository.agent_ecr.repository_url
}
