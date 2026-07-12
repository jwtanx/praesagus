resource "aws_iam_role" "ecs_task_execution" {
  name               = "praesagus-ecs-task-execution-${var.env}"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_execution_assume_role_policy.json
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task" {
  name               = "praesagus-ecs-task-${var.env}"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role_policy.json
}

resource "aws_iam_role_policy" "ecs_task_policy" {
  name = "praesagus-ecs-task-policy-${var.env}"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl",
          "s3:GetObject",
          "s3:ListBucket",
        ]
        Effect   = "Allow"
        Resource = [
          aws_s3_bucket.raw_data.arn,
          "${aws_s3_bucket.raw_data.arn}/*",
        ]
      },
      {
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Action = [
          "secretsmanager:GetSecretValue",
          "ssm:GetParameter",
          "ssm:GetParameters",
        ]
        Effect   = "Allow"
        Resource = "*"
      },
    ]
  })
}

resource "aws_ecs_cluster" "praesagus" {
  name = "praesagus-ecs-${var.env}"
}

resource "aws_ecs_task_definition" "praesagus_ingest" {
  family                   = "praesagus-ingest-${var.env}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.ecs_task_cpu
  memory                   = var.ecs_task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "ingest"
      image     = var.ecs_container_image
      essential = true
      command   = ["python", "-m", "connectors.multi_runner"]
      environment = [
        {
          name  = "RAW_DATA_BUCKET"
          value = aws_s3_bucket.raw_data.bucket
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/praesagus-ingest"
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}

resource "aws_cloudwatch_log_group" "ecs_ingest" {
  name              = "/ecs/praesagus-ingest"
  retention_in_days = 14
}

resource "aws_security_group" "ecs_task" {
  name        = "praesagus-ecs-task-sg-${var.env}"
  description = "Security group for ECS Fargate ingestion tasks"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_ecs_service" "ecs_ingest" {
  name            = "praesagus-ingest-${var.env}"
  cluster         = aws_ecs_cluster.praesagus.id
  task_definition = aws_ecs_task_definition.praesagus_ingest.arn
  desired_count   = 0
  launch_type     = "FARGATE"
  network_configuration {
    subnets         = var.public_subnet_ids
    security_groups = [aws_security_group.ecs_task.id]
    assign_public_ip = true
  }
}

resource "aws_iam_policy_document" "ecs_task_execution_assume_role_policy" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_policy_document" "ecs_task_assume_role_policy" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}
