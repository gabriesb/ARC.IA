output "github_actions_role_arn" {
  description = "ARN da role assumida pelo GitHub Actions via OIDC — adicione como variável AWS_ROLE_ARN no repositório"
  value       = aws_iam_role.github_actions_ecr_role.arn
}