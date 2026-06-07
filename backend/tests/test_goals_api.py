import pytest


@pytest.mark.asyncio
async def test_create_goal_returns_200(client, mock_pipeline):
    resp = await client.post(
        "/api/v1/goals",
        json={"raw_input": "이번 달 토익 900점", "available_hours": {"weekday": 2, "weekend": 4}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "goal" in body
    assert "milestones" in body
    assert "todos" in body
    assert body["goal"]["title"] == "토익 900점 달성"
    assert len(body["milestones"]) == 4


@pytest.mark.asyncio
async def test_list_goals_empty(client):
    resp = await client.get("/api/v1/goals")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_goal_not_found(client):
    resp = await client.get("/api/v1/goals/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_then_get_goal(client, mock_pipeline):
    create_resp = await client.post(
        "/api/v1/goals",
        json={"raw_input": "이번 달 토익 900점", "available_hours": {"weekday": 2, "weekend": 4}},
    )
    goal_id = create_resp.json()["goal"]["id"]
    get_resp = await client.get(f"/api/v1/goals/{goal_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == goal_id


@pytest.mark.asyncio
async def test_smart_reschedule_goal_endpoint(client, mock_pipeline):
    # 1. 목표 생성
    create_resp = await client.post(
        "/api/v1/goals",
        json={"raw_input": "이번 달 토익 900점", "available_hours": {"weekday": 2, "weekend": 4}},
    )
    goal_id = create_resp.json()["goal"]["id"]
    todo_id = create_resp.json()["todos"][0]["id"]
    
    # 2. reschedule_pipeline.ainvoke 모킹 설정
    fake_pipeline_result = {
        "overall_summary": "기한 초과된 일정을 다음 날로 순연 조율했습니다.",
        "at_risk": False,
        "suggestions": [
            {
                "todo_id": todo_id,
                "suggested_due_date": "2026-06-08",
                "reason": "가용시간에 맞춰 순연 제안"
            }
        ],
        "error": None
    }
    
    from unittest.mock import patch, AsyncMock
    with patch("app.agent.reschedule_graph.reschedule_pipeline.ainvoke", AsyncMock(return_value=fake_pipeline_result)) as mock_ainvoke:
        resp = await client.post(f"/api/v1/goals/{goal_id}/reschedule/smart")
        
        mock_ainvoke.assert_called_once()
        assert resp.status_code == 200
        body = resp.json()
        assert body["goal_id"] == goal_id
        assert body["overall_summary"] == "기한 초과된 일정을 다음 날로 순연 조율했습니다."
        assert body["at_risk"] is False
        assert len(body["suggestions"]) == 1
        assert body["suggestions"][0]["todo_id"] == todo_id
        assert body["suggestions"][0]["reason"] == "가용시간에 맞춰 순연 제안"


@pytest.mark.asyncio
async def test_smart_reschedule_goal_not_found(client):
    resp = await client.post("/api/v1/goals/9999/reschedule/smart")
    assert resp.status_code == 404
