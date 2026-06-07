import asyncio
import json
import re
from datetime import date

from app.agent.client import client
from app.agent.state import RescheduleState

_SYSTEM = """당신은 목표 관리 에이전트입니다. 사용자의 목표 진척도 및 가용 시간 데이터를 분석하고, 미완료된 할 일(Todo)들의 지능적인 재배치 제안과 그에 따른 한글 분석 요약(코멘트)을 작성하세요.

[규칙]
1. Goal의 deadline을 초과하여 할 일을 재배치할 수 없습니다. (제안하는 모든 suggested_due_date <= deadline)
2. 각 날짜에 배분된 할 일들의 예상 소요 시간(estimated_minutes) 합이 사용자의 일일 가용 시간(available_hours)을 초과하지 않도록 분산 배정하세요.
3. 만약 남은 총 소요시간이 데드라인까지의 가용 시간 한계를 절대적으로 초과하는 경우, 최대한 타이트하게 배정하고 overall_summary에 "목표 데드라인을 연장하거나 일부 할 일을 제거/축소해야 함"을 명확히 조언하세요.
4. 이미 완료된(is_done=true) 할 일은 절대 재배치 제안에 포함하지 마세요.
5. 출력은 반드시 아래의 JSON 포맷만 반환하세요 (어떠한 설명이나 백틱 마크다운도 포함 금지):
{
  "overall_summary": "1~2문장 한국어 요약 피드백",
  "at_risk": true 또는 false,
  "suggestions": [
    {
      "todo_id": 할일ID,
      "suggested_due_date": "YYYY-MM-DD",
      "reason": "해당 할 일을 이 날짜로 조정한 구체적인 사유 (한국어)"
    }
  ]
}"""


async def smart_reschedule_node(state: RescheduleState) -> dict:
    if state.get("error") or not state.get("analysis"):
        return {}
        
    analysis = state["analysis"]
    today = date.today()
    
    # 미완료 할 일 정리
    pending_todos_info = []
    for ms in state.get("milestones", []):
        for todo in ms.todos:
            if not todo.is_done:
                pending_todos_info.append(
                    f"- [ID: {todo.id}] {todo.title} (기존 예정일: {todo.due_date}, 예상: {todo.estimated_minutes}분)"
                )
                
    pending_text = "\n".join(pending_todos_info) if pending_todos_info else "미완료 할 일 없음"
    
    prompt = (
        f"목표: {state['goal_title']}\n"
        f"데드라인: {state['deadline']}\n"
        f"오늘 날짜: {today}\n"
        f"사용자 가용 시간 — 평일: 하루 {state.get('available_hours_weekday', 2)}시간, 주말: 하루 {state.get('available_hours_weekend', 4)}시간\n\n"
        f"[현재 진척 분석]\n"
        f"- 전체 할 일 개수: {analysis['total_todos']}개\n"
        f"- 완료된 할 일 개수: {analysis['done_todos']}개 (완료율: {analysis['progress_rate']}%)\n"
        f"- 기한 초과(Overdue) 할 일 개수: {analysis['overdue_todos']}개\n"
        f"- 남은 미완료 할 일들의 예상 소요 시간 합: {analysis['total_estimated_minutes_remaining']}분\n"
        f"- 데드라인까지 남은 총 가용 시간: {analysis['available_minutes_remaining']}분\n"
        f"- 현재 지연 위험 상태(at_risk): {'예' if analysis['at_risk'] else '아니오'}\n\n"
        f"[미완료 할 일 목록]\n"
        f"{pending_text}"
    )
    
    max_retries = 3
    response = None
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            response = await asyncio.wait_for(
                client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=4096,
                    system=_SYSTEM,
                    messages=[{"role": "user", "content": prompt}],
                ),
                timeout=50.0
            )
            break
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                
    if response is None:
        return {"error": f"smart_reschedule: Claude API failed after {max_retries} attempts. Last error: {last_exception}"}
        
    try:
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return {"error": "smart_reschedule: JSON block not found in LLM response"}
            
        data = json.loads(match.group())
        
        # 날짜 포맷 검증 및 데드라인 초과 방어
        deadline = state["deadline"]
        clean_suggestions = []
        for sug in data.get("suggestions", []):
            todo_id = sug.get("todo_id")
            sug_date_str = sug.get("suggested_due_date")
            reason = sug.get("reason", "")
            
            if todo_id is None or not sug_date_str:
                continue
            try:
                sug_date = date.fromisoformat(sug_date_str)
                # 데드라인 초과 방지
                sug_date = min(sug_date, deadline)
            except ValueError:
                continue
                
            clean_suggestions.append({
                "todo_id": todo_id,
                "suggested_due_date": sug_date,
                "reason": reason
            })
            
        return {
            "overall_summary": data.get("overall_summary", ""),
            "at_risk": data.get("at_risk", analysis["at_risk"]),
            "suggestions": clean_suggestions
        }
        
    except json.JSONDecodeError as e:
        return {"error": f"smart_reschedule: invalid JSON from LLM — {e}"}
    except Exception as e:
        return {"error": f"smart_reschedule: {e}"}
