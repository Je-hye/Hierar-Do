from datetime import date, timedelta
from app.agent.state import RescheduleState


def analyze_progress_node(state: RescheduleState) -> dict:
    if state.get("error"):
        return {}

    milestones = state.get("milestones", [])
    today = date.today()
    
    total_todos = 0
    done_todos = 0
    overdue_todos = 0
    total_estimated = 0
    total_actual = 0
    
    for ms in milestones:
        for todo in ms.todos:
            total_todos += 1
            if todo.is_done:
                done_todos += 1
                total_actual += todo.actual_minutes if todo.actual_minutes is not None else todo.estimated_minutes
            else:
                total_estimated += todo.estimated_minutes
                if todo.due_date and todo.due_date < today:
                    overdue_todos += 1

    progress_rate = round(done_todos / total_todos * 100) if total_todos > 0 else 0
    
    # 남은 일수 계산
    deadline = state["deadline"]
    days_remaining = max((deadline - today).days, 0)
    
    # 오늘부터 deadline까지의 총 가용 시간(분) 계산
    available_minutes_remaining = 0
    current = today
    while current <= deadline:
        if current.weekday() >= 5:
            available_minutes_remaining += state.get("available_hours_weekend", 4) * 60
        else:
            available_minutes_remaining += state.get("available_hours_weekday", 2) * 60
        current += timedelta(days=1)
        
    # 위험 판단: 기한 초과 Todo가 있거나, 남은 가용 시간 대비 미완료 Todo들의 총 요구 시간이 초과할 경우
    at_risk = overdue_todos > 0 or total_estimated > available_minutes_remaining
    
    return {
        "analysis": {
            "total_todos": total_todos,
            "done_todos": done_todos,
            "overdue_todos": overdue_todos,
            "progress_rate": progress_rate,
            "total_estimated_minutes_remaining": total_estimated,
            "total_actual_minutes_spent": total_actual,
            "days_remaining": days_remaining,
            "available_minutes_remaining": available_minutes_remaining,
            "at_risk": at_risk
        }
    }
