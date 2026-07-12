# CI/CD & IaC Strategy

Status: Draft

IaC

- Use Terraform for provisioning core infra: S3 buckets, IAM roles, EventBridge, VPC, RDS, DynamoDB.
- Keep environment-specific variables outside repo and in a secure parameter store.

CI/CD

- GitHub Actions or AWS CodeBuild for CI pipelines.
- Pipeline: lint → unit tests → build container → push to ECR → deploy to dev.
- Use TF plan approvals for infra changes; apply in staging after manual review.

Environments

- dev, staging, prod with separate AWS accounts or isolated environments.
