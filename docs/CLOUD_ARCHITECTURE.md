# Cloud Architecture

Status: Draft

Preferred Cloud: AWS

Services and Roles

- S3: Raw and transformed storage
- ECS Fargate: containerized connectors and workers. Use short-lived tasks with dynamic public IP assignment for ingestion to reduce the risk of being banned or rate limited.
- Lambda: small event-driven functions
- MWAA (Airflow): orchestration for complex DAGs
- EventBridge: event bus for decoupled communication
- SQS/SNS: durable queues and notifications
- DynamoDB / Aurora: feature store and transactional metadata
- OpenSearch: search and analytics
- Glue / Athena: serverless ETL and ad-hoc queries
- CloudWatch: metrics, logs, alarms
- ECR: container registry

Network & Security

- VPC with private subnets for stateful services; NAT for egress.
- ALB + Cognito (or OIDC) for API auth in front of API Gateway/ALB.
- KMS for encryption at rest for S3 and databases.

CI/CD & IaC

- Use Terraform for infra provisioning.
- GitHub Actions or CodeBuild for CI pipelines.

Cost Management

- Prefer serverless where cost-effective (Lambda, Glue).
- Use lifecycle policies and TTLs on warm stores; tier older data to cheaper classes.
