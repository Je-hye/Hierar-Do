"""LLM 노드 단위 테스트 (Anthropic 클라이언트 모킹)

실제 API를 호출하지 않고 parse_goal, decompose 노드의 파싱 로직과
에러 처리를 검증합니다.
"""

import json
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.nodes.parse_goal import parse_goal_node
from app.agent.nodes.decompose import decompose_node


def _make_llm_response(text: str):
    """Anthropic 응답 객체를 흉내내는 Mock 생성."""
    content = MagicMock()
    content.text = text
    response = MagicMock()
    response.content = [content]
    return response


@pytest.fixture
def base_state():
    today = date.today()
    return {
        "raw_input": "이번 달 안에 토익 900점 받고 싶어",
        "available_hours": {"weekday": 2, "weekend": 4},
        "goal": None,
        "milestones": [],
        "error": None,
    }


# ─── parse_goal_node 테스트 ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_parse_goal_success(base_state):
    """정상적인 JSON 응답을 파싱하여 ParsedGoal을 반환하는지 검증."""
    deadline = (date.today() + timedelta(days=30)).isoformat()
    llm_json = json.dumps({"title": "토익 900점 달성", "deadline": deadline})

    with patch("app.agent.nodes.parse_goal.client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=_make_llm_response(llm_json))
        result = await parse_goal_node(base_state)

    assert "goal" in result
    assert result["goal"].title == "토익 900점 달성"
    assert result["goal"].deadline.isoformat() == deadline
    assert "error" not in result


@pytest.mark.asyncio
async def test_parse_goal_markdown_fence(base_state):
    """LLM이 마크다운 코드펜스로 감싼 JSON을 반환해도 정상 파싱하는지 검증."""
    deadline = (date.today() + timedelta(days=30)).isoformat()
    llm_json = f"```json\n{{\"title\": \"토익 900점\", \"deadline\": \"{deadline}\"}}\n```"

    with patch("app.agent.nodes.parse_goal.client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=_make_llm_response(llm_json))
        result = await parse_goal_node(base_state)

    assert "goal" in result
    assert result["goal"].title == "토익 900점"


@pytest.mark.asyncio
async def test_parse_goal_default_deadline(base_state):
    """deadline이 없으면 오늘 기준 30일 후로 기본 설정되는지 검증."""
    llm_json = json.dumps({"title": "토익 900점 달성"})

    with patch("app.agent.nodes.parse_goal.client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=_make_llm_response(llm_json))
        result = await parse_goal_node(base_state)

    expected_deadline = date.today() + timedelta(days=30)
    assert result["goal"].deadline == expected_deadline


@pytest.mark.asyncio
async def test_parse_goal_invalid_json(base_state):
    """LLM이 JSON이 아닌 텍스트를 반환하면 error를 반환하는지 검증."""
    with patch("app.agent.nodes.parse_goal.client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=_make_llm_response("죄송합니다, 잘 모르겠어요."))
        result = await parse_goal_node(base_state)

    assert "error" in result
    assert result["error"].startswith("parse_goal:")


@pytest.mark.asyncio
async def test_parse_goal_api_error(base_state):
    """Anthropic API 호출 자체가 실패하면 error를 반환하는지 검증."""
    with patch("app.agent.nodes.parse_goal.client") as mock_client:
        mock_client.messages.create = AsyncMock(side_effect=Exception("API rate limit"))
        result = await parse_goal_node(base_state)

    assert "error" in result
    assert "parse_goal" in result["error"]


# ─── decompose_node 테스트 ────────────────────────────────────────────────────

@pytest.fixture
def state_with_goal(base_state):
    from app.agent.state import ParsedGoal
    base_state["goal"] = ParsedGoal(
        title="토익 900점 달성",
        deadline=date.today() + timedelta(days=30),
    )
    return base_state


@pytest.mark.asyncio
async def test_decompose_success(state_with_goal):
    """4개 마일스톤과 각 할 일을 올바르게 파싱하는지 검증."""
    milestones = [
        {"title": f"{i+1}주차 목표", "week_number": i + 1, "todos": [
            {"title": f"할 일 {j+1}", "estimated_minutes": 30} for j in range(3)
        ]}
        for i in range(4)
    ]

    with patch("app.agent.nodes.decompose.client") as mock_client:
        mock_client.messages.create = AsyncMock(
            return_value=_make_llm_response(json.dumps(milestones))
        )
        result = await decompose_node(state_with_goal)

    assert "milestones" in result
    assert len(result["milestones"]) == 4
    assert len(result["milestones"][0].todos) == 3


@pytest.mark.asyncio
async def test_decompose_skips_on_error(base_state):
    """상위 노드에서 에러가 있으면 decompose를 건너뛰는지 검증."""
    base_state["error"] = "parse_goal: 에러 발생"
    result = await decompose_node(base_state)
    assert result == {}


@pytest.mark.asyncio
async def test_decompose_wrong_milestone_count(state_with_goal):
    """마일스톤 개수가 4개가 아니면 에러를 반환하는지 검증."""
    milestones = [
        {"title": "1주차", "week_number": 1, "todos": [{"title": "할 일", "estimated_minutes": 30}]}
    ]

    with patch("app.agent.nodes.decompose.client") as mock_client:
        mock_client.messages.create = AsyncMock(
            return_value=_make_llm_response(json.dumps(milestones))
        )
        result = await decompose_node(state_with_goal)

    assert "error" in result
    assert "expected 4 milestones" in result["error"]


@pytest.mark.asyncio
async def test_decompose_invalid_json(state_with_goal):
    """LLM이 JSON이 아닌 텍스트를 반환하면 에러를 반환하는지 검증."""
    with patch("app.agent.nodes.decompose.client") as mock_client:
        mock_client.messages.create = AsyncMock(
            return_value=_make_llm_response("마일스톤을 생성할 수 없습니다.")
        )
        result = await decompose_node(state_with_goal)

    assert "error" in result
    assert "decompose" in result["error"]
