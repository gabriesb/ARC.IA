output "diagram_bucket_name" {
  description = "Nome do bucket S3 (criado em infra_aws/) onde os diagramas .drawio gerados sao armazenados."
  value       = data.aws_s3_bucket.diagrams.bucket
}

output "github_token_secret_arn" {
  description = "ARN do secret no Secrets Manager (criado em infra_aws/) onde o GitHub PAT deve ser configurado (fora do Terraform, ex: aws secretsmanager put-secret-value)."
  value       = data.aws_secretsmanager_secret.github_token.arn
}
