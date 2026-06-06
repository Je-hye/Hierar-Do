import pytest


@pytest.mark.asyncio
async def test_preview_empty_when_no_goals(client):
    resp = await client.post("/api/v1/reschedule/preview")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_apply_empty_when_no_goals(client):
    resp = await client.post("/api/v1/reschedule/apply")
    assert resp.status_code == 200
    assert resp.json() == {"updated": 0}


@pytest.mark.asyncio
async def test_preview_empty_when_all_todos_done(client, mock_pipeline):
    create_resp = await client.post(
        "/api/v1/goals",
        json={"raw_input": "이번 달 토익 900점 목표", "available_hours": {"weekday": 2, "weekend": 4}},
    )
    todos = create_resp.json()["todos"]
    for todo in todos:
        await client.patch(f"/api/v1/todos/{todo['id']}/done")

    resp = await client.post("/api/v1/reschedule/preview")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_preview_returns_rescheduled_items(client, mock_pipeline):
    # mock creates 12 todos (4 milestones × 3 todos) all with due_date=deadline(today+28)
    # algorithm redistributes from today → 8 of 12 get new dates
    await client.post(
        "/api/v1/goals",
        json={"raw_input": "이번 달 토익 900점 목표", "available_hours": {"weekday": 2, "weekend": 4}},
    )
    resp = await client.post("/api/v1/reschedule/preview")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) > 0
    for item in items:
        assert item["old_due_date"] != item["new_due_date"]
        assert "todo_id" in item
        assert "title" in item
        assert "new_due_date" in item


@pytest.mark.asyncio
async def test_apply_updates_todo_due_dates(client, mock_pipeline):
    await client.post(
        "/api/v1/goals",
        json={"raw_input": "이번 달 토익 900점 목표", "available_hours": {"weekday": 2, "weekend": 4}},
    )
    preview_items = (await client.post("/api/v1/reschedule/preview")).json()
    assert len(preview_items) > 0

    resp = await client.post("/api/v1/reschedule/apply")
    assert resp.status_code == 200
    assert resp.json()["updated"] == len(preview_items)


@pytest.mark.asyncio
async def test_apply_is_idempotent(client, mock_pipeline):
    await client.post(
        "/api/v1/goals",
        json={"raw_input": "이번 달 토익 900점 목표", "available_hours": {"weekday": 2, "weekend": 4}},
    )
    first = await client.post("/api/v1/reschedule/apply")
    assert first.json()["updated"] > 0

    second = await client.post("/api/v1/reschedule/apply")
    assert second.json()["updated"] == 0


@pytest.mark.asyncio
async def test_preview_excludes_done_goals(client, mock_pipeline):
    # Create a goal
    create_resp = await client.post(
        "/api/v1/goals",
        json={"raw_input": "이번 달 토익 900점 목표", "available_hours": {"weekday": 2, "weekend": 4}},
    )
    goal_id = create_resp.json()["goal"]["id"]

    # Verify preview has items before marking goal done
    preview_before = (await client.post("/api/v1/reschedule/preview")).json()
    assert len(preview_before) > 0

    # Directly update goal status to 'done' in the test DB
    from sqlalchemy import update
    from app.models.goal import Goal, GoalStatus
    from app.db.session import get_db
    from app.main import app

    db_override = app.dependency_overrides.get(get_db)
    async for db in db_override():
        await db.execute(
            update(Goal).where(Goal.id == goal_id).values(status=GoalStatus.done)
        )
        await db.commit()
        break

    # Preview should now be empty (done goal excluded)
    preview_after = (await client.post("/api/v1/reschedule/preview")).json()
    assert preview_after == []
