import pytest
from datetime import date, timedelta
from unittest.mock import patch, AsyncMock

from app.agent.state import RescheduleState, RescheduleMilestoneInfo, RescheduleTodoInfo
from app.agent.nodes.analyze_progress import analyze_progress_node
from app.agent.nodes.smart_reschedule import smart_reschedule_node


def test_analyze_progress_node():
    today = date.today()
    deadline = today + timedelta(days=10)
    
    # 2개의 마일스톤, 각각 2개의 할 일
    # 총 4개 중 2개 완료, 1개 지연, 1개 미완료(예정)
    milestones = [
        RescheduleMilestoneInfo(
            id=1,
            title="마일스톤 1",
            week_number=1,
            todos=[
                RescheduleTodoInfo(id=10, title="할일 1", estimated_minutes=30, actual_minutes=40, is_done=True),
                RescheduleTodoInfo(id=11, title="할일 2", estimated_minutes=60, due_date=today - timedelta(days=1), is_done=False) # 지연
            ]
        ),
        RescheduleMilestoneInfo(
            id=2,
            title="마일스톤 2",
            week_number=2,
            todos=[
                RescheduleTodoInfo(id=20, title="할일 3", estimated_minutes=30, is_done=True), # actual_minutes=None -> estimated 적용
                RescheduleTodoInfo(id=21, title="할일 4", estimated_minutes=60, due_date=today + timedelta(days=2), is_done=False) # 예정
            ]
        )
    ]
    
    state = RescheduleState(
        goal_id=1,
        goal_title="테스트 목표",
        deadline=deadline,
        available_hours_weekday=2,
        available_hours_weekend=4,
        milestones=milestones,
        analysis=None,
        overall_summary=None,
        at_risk=None,
        suggestions=None,
        error=None
    )
    
    result = analyze_progress_node(state)
    analysis = result["analysis"]
    
    assert analysis["total_todos"] == 4
    assert analysis["done_todos"] == 2
    assert analysis["progress_rate"] == 50
    assert analysis["overdue_todos"] == 1
    assert analysis["total_estimated_minutes_remaining"] == 120 # 60 + 60
    assert analysis["total_actual_minutes_spent"] == 70 # 40 + 30
    assert analysis["days_remaining"] == 10
    assert analysis["at_risk"] is True # overdue가 있으므로 위험군 분류


@pytest.mark.asyncio
async def test_smart_reschedule_node_mocked():
    today = date.today()
    deadline = today + timedelta(days=10)
    
    state = RescheduleState(
        goal_id=1,
        goal_title="테스트 목표",
        deadline=deadline,
        available_hours_weekday=2,
        available_hours_weekend=4,
        milestones=[
            RescheduleMilestoneInfo(
                id=1,
                title="마일스톤 1",
                week_number=1,
                todos=[
                    RescheduleTodoInfo(id=10, title="할일 1", estimated_minutes=30, due_date=today - timedelta(days=1), is_done=False)
                ]
            )
        ],
        analysis={
            "total_todos": 1,
            "done_todos": 0,
            "overdue_todos": 1,
            "progress_rate": 0,
            "total_estimated_minutes_remaining": 30,
            "total_actual_minutes_spent": 0,
            "days_remaining": 10,
            "available_minutes_remaining": 1200,
            "at_risk": True
        },
        overall_summary=None,
        at_risk=None,
        suggestions=None,
        error=None
    )
    
    fake_llm_response = """
    {
      "overall_summary": "기한 초과된 일정을 다음 날로 순연 조율했습니다.",
      "at_risk": false,
      "suggestions": [
        {
          "todo_id": 10,
          "suggested_due_date": "2026-06-08",
          "reason": "평일 가용시간에 맞춰 하루 순연 제안"
        }
      ]
    }
    """
    
    from unittest.mock import MagicMock
    mock_content_item = MagicMock()
    mock_content_item.text = fake_llm_response
    
    mock_response = MagicMock()
    mock_response.content = [mock_content_item]
    
    mock_create = AsyncMock(return_value=mock_response)
    
    with patch("app.agent.nodes.smart_reschedule.client.messages.create", mock_create):
        result = await smart_reschedule_node(state)
        
        print("RESULT IS:", result)
        mock_create.assert_called_once()
        assert "error" not in result, f"Node returned error: {result.get('error')}"
        assert result["overall_summary"] == "기한 초과된 일정을 다음 날로 순연 조율했습니다."
        assert result["at_risk"] is False
        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["todo_id"] == 10
        assert result["suggestions"][0]["reason"] == "평일 가용시간에 맞춰 하루 순연 제안"
