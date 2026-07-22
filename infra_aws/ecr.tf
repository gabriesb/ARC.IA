resource "aws_ecr_repository" "agent_ecr" {
  name                 = "agent_ecr"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}


