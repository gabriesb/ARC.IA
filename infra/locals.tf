resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  suffix       = random_id.suffix.hex
  runtime_name = "${var.project_name}-${local.suffix}"
  role_name    = "bedrock-agent-runtime-role-${local.suffix}"
}