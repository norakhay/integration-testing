import os
from uuid import uuid4

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

from api.todo import app

TABLE_NAME = "todo-tasks"


@pytest.fixture
def dynamodb_table():
    with mock_aws():
        os.environ["TABLE_NAME"] = TABLE_NAME
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"

        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "task_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "task_id", "AttributeType": "S"},
                {"AttributeName": "user_id", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "user-index",
                    "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5,
                    },
                }
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        yield table


@pytest.fixture
def client(dynamodb_table):
    with TestClient(app) as test_client:
        yield test_client


def test_can_put_and_get_task(client, dynamodb_table):
    user_id = f"user_{uuid4().hex}"
    content = f"task content: {uuid4().hex}"

    create_response = client.put(
        "/create-task",
        json={"user_id": user_id, "content": content},
    )
    assert create_response.status_code == 200
    task = create_response.json()["task"]
    task_id = task["task_id"]

    stored = dynamodb_table.get_item(Key={"task_id": task_id}).get("Item")
    assert stored is not None
    assert stored["content"] == content
    assert stored["user_id"] == user_id

    get_response = client.get(f"/get-task/{task_id}")
    assert get_response.status_code == 200
    assert get_response.json()["content"] == content


def test_can_list_tasks(client):
    user_id = f"user_{uuid4().hex}"
    for i in range(3):
        create_response = client.put(
            "/create-task",
            json={"user_id": user_id, "content": f"task_{i}"},
        )
        assert create_response.status_code == 200

    response = client.get(f"/list-tasks/{user_id}")
    assert response.status_code == 200
    assert len(response.json()["tasks"]) == 3


def test_can_update_task(client, dynamodb_table):
    user_id = f"user_{uuid4().hex}"
    create_response = client.put(
        "/create-task",
        json={"user_id": user_id, "content": "task content"},
    )
    task_id = create_response.json()["task"]["task_id"]
    new_content = f"updated task content: {uuid4().hex}"

    update_response = client.put(
        "/update-task",
        json={"content": new_content, "task_id": task_id, "is_done": True},
    )
    assert update_response.status_code == 200

    stored = dynamodb_table.get_item(Key={"task_id": task_id}).get("Item")
    assert stored["content"] == new_content
    assert stored["is_done"] is True

    get_response = client.get(f"/get-task/{task_id}")
    assert get_response.status_code == 200
    assert get_response.json()["content"] == new_content
    assert get_response.json()["is_done"] is True


def test_can_delete_task(client, dynamodb_table):
    user_id = f"user_{uuid4().hex}"
    create_response = client.put(
        "/create-task",
        json={"user_id": user_id, "content": "task1"},
    )
    task_id = create_response.json()["task"]["task_id"]

    delete_response = client.delete(f"/delete-task/{task_id}")
    assert delete_response.status_code == 200

    stored = dynamodb_table.get_item(Key={"task_id": task_id}).get("Item")
    assert stored is None

    get_response = client.get(f"/get-task/{task_id}")
    assert get_response.status_code == 404

