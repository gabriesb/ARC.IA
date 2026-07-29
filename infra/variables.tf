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

variable "image_tag" {
  description = "Tag da imagem Docker no ECR (SHA do commit). Passada pelo CI/CD para forcar atualizacao do runtime."
  type        = string
  default     = "latest"
}
