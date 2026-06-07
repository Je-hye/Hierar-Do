import pytest


@pytest.mark.asyncio
async def test_mark_todo_done(client, mock_pipeline):
    create_resp = await client.post(
        "/api/v1/goals",
        json={"raw_input": "테스트 목표", "available_hours": {"weekday": 2, "weekend": 4}},
    )
    todos = create_resp.json()["todos"]
    todo_id = todos[0]["id"]

    resp = await client.patch(f"/api/v1/todos/{todo_id}/done")
    assert resp.status_code == 200
    assert resp.json()["is_done"] is True


@pytest.mark.asyncio
async def test_mark_todo_undone(client, mock_pipeline):
    create_resp = await client.post(
        "/api/v1/goals",
        json={"raw_input": "테스트 목표", "available_hours": {"weekday": 2, "weekend": 4}},
    )
    todo_id = create_resp.json()["todos"][0]["id"]

    await client.patch(f"/api/v1/todos/{todo_id}/done")
    resp = await client.patch(f"/api/v1/todos/{todo_id}/undone")
    assert resp.status_code == 200
    assert resp.json()["is_done"] is False


@pytest.mark.asyncio
async def test_todo_not_found(client):
    resp = await client.patch("/api/v1/todos/9999/done")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_todo_actual_minutes(client, mock_pipeline):
    create_resp = await client.post(
        "/api/v1/goals",
        json={"raw_input": "테스트 목표", "available_hours": {"weekday": 2, "weekend": 4}},
    )
    todo_id = create_resp.json()["todos"][0]["id"]

    # 기본값은 None이어야 함
    assert create_resp.json()["todos"][0]["actual_minutes"] is None

    # actual_minutes 업데이트
    resp = await client.patch(f"/api/v1/todos/{todo_id}", json={"actual_minutes": 45})
    assert resp.status_code == 200
    assert resp.json()["actual_minutes"] == 45


@pytest.mark.asyncio
async def test_create_todo_with_actual_minutes(client, mock_pipeline):
    create_resp = await client.post(
        "/api/v1/goals",
        json={"raw_input": "테스트 목표", "available_hours": {"weekday": 2, "weekend": 4}},
    )
    milestone_id = create_resp.json()["milestones"][0]["id"]

    # 수동 Todo 생성 시 actual_minutes 설정
    resp = await client.post(
        "/api/v1/todos",
        json={
            "milestone_id": milestone_id,
            "title": "수동 추가 일감",
            "estimated_minutes": 60,
            "actual_minutes": 90,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["actual_minutes"] == 90
