import json
import re

from app.agent.client import client
from app.agent.state import HierarDoState, ParsedMilestone, ParsedTodo
from app.agent.embeddings import search_similar_goals
from app.db.session import AsyncSessionLocal

_SYSTEM = """You are a task decomposition assistant. Break the given goal into exactly 4 weekly milestones.
Each milestone must have 3-5 daily todos with realistic estimated_minutes (15-120).

Return ONLY a valid JSON array:
[
  {
    "title": "milestone title (Korean OK)",
    "week_number": 1,
    "todos": [
      {"title": "todo title (Korean OK)", "estimated_minutes": 30}
    ]
  }
]

No explanation — JSON array only.

If past similar goals are provided, analyze their completion patterns and time estimates, and apply realistic constraints to your new suggestions (e.g., if past goals took longer than expected, allocate more time)."""


async def decompose_node(state: HierarDoState) -> dict:
    if state.get("error") or state.get("goal") is None:
        return {}
    goal = state["goal"]
    user_id = state.get("user_id")

    past_context = ""
    if user_id:
        async with AsyncSessionLocal() as db:
            past_goals = await search_similar_goals(db, user_id, state['raw_input'], limit=2)
            if past_goals:
                past_context = "\n\n[Past Similar Goals & Completion Patterns]\n"
                for i, pg in enumerate(past_goals):
                    past_context += f"--- Past Goal {i+1} ---\n{pg}\n"
    
    prompt = (
        f"Goal: {goal.title}\n"
        f"Original input: {state['raw_input']}\n"
        f"Deadline: {goal.deadline}\n"
        f"Available hours per day — weekday: {state['available_hours'].get('weekday', 2)}h, "
        f"weekend: {state['available_hours'].get('weekend', 4)}h"
        f"{past_context}"
    )
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        # JSON 배열만 추출 (앞뒤 설명 텍스트 방어)
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            return {"error": "decompose: JSON array not found in LLM response"}
        data = json.loads(match.group())
        if len(data) != 4:
            return {"error": f"decompose: expected 4 milestones, got {len(data)}"}
        milestones = [
            ParsedMilestone(
                title=m["title"],
                week_number=m["week_number"],
                todos=[ParsedTodo(**t) for t in m["todos"]],
            )
            for m in data
        ]
        return {"milestones": milestones}
    except json.JSONDecodeError as e:
        return {"error": f"decompose: invalid JSON from LLM — {e}"}
    except Exception as e:
        return {"error": f"decompose: {e}"}
