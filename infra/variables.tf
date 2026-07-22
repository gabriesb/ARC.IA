variable project_name{
  description = "Nome do projeto, usado como prefixo para nomes de recursos."
  type = string
  default = "agentcore"
}

variable "aws_region" {
  description = "Regiao AWS onde os recursos serao criados."
  type        = string
  default     = "us-east-1"
}

variable "build_branch" {
  description = "Branch do GitHub que o CodeBuild vai clonar para buildar a imagem."
  type        = string
  default     = "devops_agent"
}