"""
Deterministic mapping between Terraform AWS resource types and the official
AWS icon set bundled with draw.io / diagrams.net (the "aws4" stencil family,
`shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.<icon>`).

This mapping is the single source of truth used to render architecture
diagrams. It is intentionally rule-based (no LLM involved): a Terraform
resource type always renders with the same icon, category and color.

To add support for a new resource type, add an entry to `RESOURCE_ICON_MAP`.
Unmapped resource types still show up in the diagram using the generic
"resource" icon (`mxgraph.aws4.resource`) so nothing is silently dropped.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class IconSpec:
    icon: str          # aws4 resIcon name (without the "mxgraph.aws4." prefix)
    category: str       # used to group/color columns in the diagram
    label: str          # human friendly label prefix


# Category -> fill color (approximate AWS architecture-icons category colors)
CATEGORY_COLORS = {
    "Compute": "#ED7100",
    "Containers": "#ED7100",
    "Storage": "#7AA116",
    "Database": "#527FFF",
    "Integration": "#E7157B",
    "Network": "#8C4FFF",
    "Security": "#DD344C",
    "Analytics": "#7AA116",
    "AI/ML": "#01A88D",
    "Management": "#E7157B",
    "Other": "#232F3E",
}

# Resource types that are pure "wiring" (policies, attachments, permissions,
# associations) and therefore are NOT rendered as their own node. They are
# still allowed to appear in the parsed resource list (so callers can see
# them), but the diagram builder filters them out before layout.
NON_VISUAL_RESOURCE_TYPES = {
    "aws_iam_role_policy",
    "awscc_iam_role_policy",
    "aws_iam_role_policy_attachment",
    "aws_iam_policy_attachment",
    "aws_iam_user_policy_attachment",
    "aws_iam_group_policy_attachment",
    "aws_lambda_permission",
    "aws_route_table_association",
    "aws_route",
    "aws_security_group_rule",
    "aws_s3_bucket_policy",
    "aws_s3_bucket_public_access_block",
    "aws_s3_bucket_versioning",
    "aws_s3_bucket_server_side_encryption_configuration",
    "aws_ecr_lifecycle_policy",
    "aws_cloudwatch_log_subscription_filter",
    "aws_sns_topic_policy",
    "aws_sqs_queue_policy",
    "aws_lb_listener",
    "aws_lb_listener_rule",
    "aws_apigatewayv2_integration",
    "aws_apigatewayv2_route",
    "aws_apigatewayv2_stage",
    "aws_api_gateway_deployment",
    "aws_api_gateway_stage",
    "random_id",
    "null_resource",
}


RESOURCE_ICON_MAP: dict[str, IconSpec] = {
    # Compute
    "aws_instance": IconSpec("ec2", "Compute", "EC2 Instance"),
    "aws_launch_template": IconSpec("ec2", "Compute", "Launch Template"),
    "aws_launch_configuration": IconSpec("ec2", "Compute", "Launch Configuration"),
    "aws_autoscaling_group": IconSpec("ec2", "Compute", "Auto Scaling Group"),
    "aws_lambda_function": IconSpec("lambda", "Compute", "Lambda"),
    "aws_lambda_alias": IconSpec("lambda", "Compute", "Lambda Alias"),
    "aws_batch_job_definition": IconSpec("batch", "Compute", "Batch Job"),
    "aws_elastic_beanstalk_environment": IconSpec("elastic_beanstalk", "Compute", "Elastic Beanstalk"),

    # Containers
    "aws_ecs_cluster": IconSpec("ecs", "Containers", "ECS Cluster"),
    "aws_ecs_service": IconSpec("ecs", "Containers", "ECS Service"),
    "aws_ecs_task_definition": IconSpec("ecs", "Containers", "ECS Task Definition"),
    "aws_eks_cluster": IconSpec("eks", "Containers", "EKS Cluster"),
    "aws_eks_node_group": IconSpec("eks", "Containers", "EKS Node Group"),
    "aws_ecr_repository": IconSpec("ecr", "Containers", "ECR Repository"),

    # Storage
    "aws_s3_bucket": IconSpec("bucket", "Storage", "S3 Bucket"),
    "aws_efs_file_system": IconSpec("elastic_file_system", "Storage", "EFS File System"),
    "aws_ebs_volume": IconSpec("volume", "Storage", "EBS Volume"),

    # Database
    "aws_dynamodb_table": IconSpec("dynamodb", "Database", "DynamoDB Table"),
    "aws_db_instance": IconSpec("rds", "Database", "RDS Instance"),
    "aws_rds_cluster": IconSpec("rds", "Database", "RDS Cluster (Aurora)"),
    "aws_rds_cluster_instance": IconSpec("rds", "Database", "RDS Cluster Instance"),
    "aws_redshift_cluster": IconSpec("redshift", "Database", "Redshift Cluster"),
    "aws_elasticache_cluster": IconSpec("elasticache", "Database", "ElastiCache Cluster"),
    "aws_elasticache_replication_group": IconSpec("elasticache", "Database", "ElastiCache Replication Group"),

    # Integration / Application Integration
    "aws_api_gateway_rest_api": IconSpec("api_gateway", "Integration", "API Gateway (REST)"),
    "aws_apigatewayv2_api": IconSpec("api_gateway", "Integration", "API Gateway (HTTP/WS)"),
    "aws_sns_topic": IconSpec("sns", "Integration", "SNS Topic"),
    "aws_sqs_queue": IconSpec("sqs", "Integration", "SQS Queue"),
    "aws_cloudwatch_event_rule": IconSpec("eventbridge", "Integration", "EventBridge Rule"),
    "aws_cloudwatch_event_bus": IconSpec("eventbridge", "Integration", "EventBridge Bus"),
    "aws_sfn_state_machine": IconSpec("step_functions", "Integration", "Step Functions"),
    "aws_appsync_graphql_api": IconSpec("appsync", "Integration", "AppSync API"),

    # Network
    "aws_vpc": IconSpec("vpc", "Network", "VPC"),
    "aws_subnet": IconSpec("vpc", "Network", "Subnet"),
    "aws_internet_gateway": IconSpec("internet_gateway", "Network", "Internet Gateway"),
    "aws_nat_gateway": IconSpec("nat_gateway", "Network", "NAT Gateway"),
    "aws_lb": IconSpec("elastic_load_balancing", "Network", "Load Balancer"),
    "aws_alb": IconSpec("elastic_load_balancing", "Network", "ALB"),
    "aws_lb_target_group": IconSpec("elastic_load_balancing", "Network", "Target Group"),
    "aws_cloudfront_distribution": IconSpec("cloudfront", "Network", "CloudFront Distribution"),
    "aws_route53_zone": IconSpec("route_53", "Network", "Route 53 Zone"),
    "aws_route53_record": IconSpec("route_53", "Network", "Route 53 Record"),

    # Security / Identity / Compliance
    "aws_secretsmanager_secret": IconSpec("secrets_manager", "Security", "Secrets Manager Secret"),
    "aws_kms_key": IconSpec("key_management_service", "Security", "KMS Key"),
    "aws_iam_role": IconSpec("identity_and_access_management", "Security", "IAM Role"),
    "awscc_iam_role": IconSpec("identity_and_access_management", "Security", "IAM Role"),
    "aws_iam_user": IconSpec("identity_and_access_management", "Security", "IAM User"),
    "aws_iam_policy": IconSpec("identity_and_access_management", "Security", "IAM Policy"),
    "aws_cognito_user_pool": IconSpec("cognito", "Security", "Cognito User Pool"),
    "aws_wafv2_web_acl": IconSpec("waf", "Security", "WAF Web ACL"),

    # Analytics
    "aws_kinesis_stream": IconSpec("kinesis_data_streams", "Analytics", "Kinesis Data Stream"),
    "aws_kinesis_firehose_delivery_stream": IconSpec("kinesis_data_firehose", "Analytics", "Kinesis Firehose"),
    "aws_glue_job": IconSpec("glue", "Analytics", "Glue Job"),
    "aws_glue_crawler": IconSpec("glue", "Analytics", "Glue Crawler"),
    "aws_athena_workgroup": IconSpec("athena", "Analytics", "Athena Workgroup"),

    # Management
    "aws_cloudwatch_log_group": IconSpec("cloudwatch_logs", "Management", "CloudWatch Log Group"),
    "aws_cloudwatch_dashboard": IconSpec("cloudwatch", "Management", "CloudWatch Dashboard"),

    # AI / ML — AgentCore/Bedrock (best-effort generic icon; no dedicated
    # aws4 stencil confirmed at the time this map was written)
    "awscc_bedrockagentcore_runtime": IconSpec("resource", "AI/ML", "Bedrock AgentCore Runtime"),
    "aws_bedrockagent_agent": IconSpec("resource", "AI/ML", "Bedrock Agent"),
    "aws_sagemaker_endpoint": IconSpec("sagemaker_2", "AI/ML", "SageMaker Endpoint"),
}

FALLBACK_ICON = IconSpec("resource", "Other", "")


def resolve_icon(tf_type: str) -> IconSpec:
    """Returns the IconSpec for a Terraform resource type, falling back to a
    generic 'resource' icon (still visible, never silently dropped) for
    unmapped types."""
    return RESOURCE_ICON_MAP.get(tf_type, FALLBACK_ICON)


def category_color(category: str) -> str:
    return CATEGORY_COLORS.get(category, CATEGORY_COLORS["Other"])
