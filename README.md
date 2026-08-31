# integration-testing

FastAPI `TestClient` tests for the todo API in `api/todo.py`. They hit the real routes and check DynamoDB writes (mocked with moto).

## Setup

```bash
pip install -r requirements.txt
```

## How the tests are written

File: `test_todo_api.py`

1. Import `TestClient` from `fastapi.testclient`.
2. Import `mock_aws` from moto, and the FastAPI `app`.
3. Create a DynamoDB table fixture inside `mock_aws` (partition key `task_id`, GSI `user-index`).
4. Create a `client` fixture that wraps `TestClient(app)`.
5. Call endpoints with `client.put`, `client.get`, and `client.delete`.
6. Assert HTTP status codes and JSON, then `dynamodb_table.get_item` to confirm the database changed.

Example:

```python
from fastapi.testclient import TestClient
from api.todo import app

def test_can_put_and_get_task(client, dynamodb_table):
    create_response = client.put(
        "/create-task",
        json={"user_id": user_id, "content": content},
    )
    assert create_response.status_code == 200
    task_id = create_response.json()["task"]["task_id"]

    stored = dynamodb_table.get_item(Key={"task_id": task_id}).get("Item")
    assert stored["content"] == content

    get_response = client.get(f"/get-task/{task_id}")
    assert get_response.status_code == 200
```

Create, list, update, and delete are covered the same way.

## Run tests

```bash
pytest
```
