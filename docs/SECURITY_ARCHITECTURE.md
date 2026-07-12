# Security Architecture

Status: Draft

Principles

- Least privilege for all IAM roles and service accounts.
- Secrets in AWS Secrets Manager; no secrets in repo.
- Encrypt data at rest (S3/KMS) and in transit (TLS).

Access Control

- Use IAM roles for services; restrict S3 prefixes per role.
- Use Cognito or OIDC for user authentication to the UI/API.

Audit & Compliance

- Enable CloudTrail and log access to sensitive resources.
- Maintain data collection provenance and legal metadata for each connector.

Incident Response

- Define runbooks for data leaks, unauthorized access, and connector abuse.
