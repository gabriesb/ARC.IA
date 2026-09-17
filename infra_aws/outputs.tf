output "github_actions_role_arn" {
  description = "ARN da role assumida pelo GitHub Actions via OIDC — adicione como variável AWS_ROLE_ARN no repositório"
  value       = aws_iam_role.github_actions_ecr_role.arn
}

output "diagram_bucket_name" {
  description = "Nome do bucket S3 onde os diagramas .drawio gerados pelo agente sao armazenados."
  value       = aws_s3_bucket.diagrams.bucket
}

output "github_token_secret_arn" {
  description = "ARN do secret no Secrets Manager onde o GitHub PAT deve ser configurado (fora do Terraform, ex: aws secretsmanager put-secret-value)."
  value       = aws_secretsmanager_secret.github_token.arn
}