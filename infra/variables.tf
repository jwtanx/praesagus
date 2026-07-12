variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "env" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "vpc_id" {
  description = "VPC ID for ECS tasks"
  type        = string
  default     = ""
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for ECS Fargate tasks with assign_public_ip"
  type        = list(string)
  default     = []
}

variable "ecs_container_image" {
  description = "Container image used by the ECS connector task"
  type        = string
  default     = "public.ecr.aws/amazonlinux/amazonlinux:2023"
}

variable "ecs_task_cpu" {
  description = "CPU units for the ECS Fargate task"
  type        = string
  default     = "512"
}

variable "ecs_task_memory" {
  description = "Memory (MB) for the ECS Fargate task"
  type        = string
  default     = "1024"
}
