#output "agentcore_runtime_id" {
  #description = "ID do AgentCore Runtime criado pelo Terraform"
  #value       = awscc_bedrockagentcore_runtime.runtime.agent_runtime_id
#}

#output "ecr_repository_name" {
  #description = "Nome do repositório ECR usado pelo runtime"
  #value       = awscc_ecr_repository.agent_runtime.repository_name
#}

#output "ecr_repository_uri" {
  #description = "URI do repositório ECR (para build e push da imagem)"
  #value       = awscc_ecr_repository.agent_runtime.repository_uri
#}