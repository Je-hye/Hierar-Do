import json
import re
from datetime import date, timedelta

from app.agent.client import client
from app.agent.state import HierarDoState, ParsedGoal

_SYSTEM = """You are a goal parsing assistant. Extract a structured goal from the user's natural language input.
Return ONLY a valid JSON object with exactly these fields:
- "title": concise goal title (Korean is fine, max 50 chars)
- "deadline": ISO date string YYYY-MM-DD (default to 30 days from today if not specified)

Today's date is {today}. No explanation — JSON only."""


async def parse_goal_node(state: HierarDoState) -> dict:
    today = date.today().isoformat()
    default_deadline = (date.today() + timedelta(days=30)).isoformat()
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            system=_SYSTEM.format(today=today),
            messages=[{"role": "user", "content": state["raw_input"]}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        # JSON 블록만 추출 (앞뒤 설명 텍스트 방어)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return {"error": "parse_goal: JSON object not found in LLM response"}
        data = json.loads(match.group())
        data.setdefault("deadline", default_deadline)
        return {"goal": ParsedGoal(**data)}
    except json.JSONDecodeError as e:
        return {"error": f"parse_goal: invalid JSON from LLM — {e}"}
    except Exception as e:
        return {"error": f"parse_goal: {e}"}
