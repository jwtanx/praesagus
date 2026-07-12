import json
import os
from typing import Any, Dict, Iterable, List, Optional

import boto3
from botocore.exceptions import ClientError

DEFAULT_CONTAINER_NAME = os.environ.get("ECS_TASK_CONTAINER_NAME", "ingest")
DEFAULT_PLATFORM_VERSION = os.environ.get("ECS_PLATFORM_VERSION", "1.4.0")
DEFAULT_LAUNCH_TYPE = os.environ.get("ECS_LAUNCH_TYPE", "FARGATE")


def parse_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def get_ecs_client(region: Optional[str] = None):
    session = boto3.Session(region_name=region)
    return session.client("ecs")


def build_network_configuration(
    subnets: List[str],
    security_groups: Optional[List[str]] = None,
    assign_public_ip: bool = True,
) -> Dict[str, Any]:
    if not subnets:
        raise ValueError("ECS subnet configuration is required for Fargate tasks")

    return {
        "awsvpcConfiguration": {
            "subnets": subnets,
            "securityGroups": security_groups or [],
            "assignPublicIp": "ENABLED" if assign_public_ip else "DISABLED",
        }
    }


def build_overrides(
    command: Optional[List[str]] = None,
    environment: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    container_override: Dict[str, Any] = {"name": DEFAULT_CONTAINER_NAME}
    if command:
        container_override["command"] = command
    if environment:
        container_override["environment"] = [
            {"name": key, "value": str(value)} for key, value in environment.items()
        ]
    return {"containerOverrides": [container_override]}


def run_fargate_task(
    cluster: str,
    task_definition: str,
    subnets: List[str],
    security_groups: Optional[List[str]] = None,
    assign_public_ip: bool = True,
    count: int = 1,
    platform_version: str = DEFAULT_PLATFORM_VERSION,
    command: Optional[List[str]] = None,
    environment: Optional[Dict[str, str]] = None,
    region: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    ecs = get_ecs_client(region)
    network_configuration = build_network_configuration(
        subnets=subnets,
        security_groups=security_groups,
        assign_public_ip=assign_public_ip,
    )
    overrides = build_overrides(command=command, environment=environment)
    params: Dict[str, Any] = {
        "cluster": cluster,
        "taskDefinition": task_definition,
        "launchType": DEFAULT_LAUNCH_TYPE,
        "networkConfiguration": network_configuration,
        "overrides": overrides,
        "count": count,
        "platformVersion": platform_version,
    }
    if tags:
        params["tags"] = [{"key": k, "value": v} for k, v in tags.items()]

    try:
        response = ecs.run_task(**params)
    except ClientError as exc:
        raise RuntimeError(f"Failed to start ECS task: {exc}") from exc

    failures = response.get("failures", [])
    if failures:
        raise RuntimeError(f"ECS task launch failures: {failures}")

    tasks = response.get("tasks", [])
    if not tasks:
        raise RuntimeError("ECS run_task returned no started tasks")

    return response


def load_list_or_env(value: Optional[str], env_name: str) -> List[str]:
    if value:
        return parse_csv(value)
    return parse_csv(os.environ.get(env_name, ""))
