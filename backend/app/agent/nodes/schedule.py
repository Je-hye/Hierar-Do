from datetime import date, timedelta

from app.agent.state import HierarDoState, ParsedMilestone


def schedule_node(state: HierarDoState) -> dict:
    if state.get("error") or not state.get("goal") or not state.get("milestones"):
        return {}
    goal = state["goal"]
    milestones = state["milestones"]
    today = date.today()
    deadline = goal.deadline

    total_days = max((deadline - today).days, 28)
    days_per_week = total_days // 4

    updated: list[ParsedMilestone] = []
    for milestone in milestones:
        week_start = today + timedelta(days=(milestone.week_number - 1) * days_per_week)
        week_end = week_start + timedelta(days=days_per_week - 1)
        if week_end > deadline:
            week_end = deadline

        n = len(milestone.todos)
        span = max((week_end - week_start).days, 1)
        updated_todos = []
        for i, todo in enumerate(milestone.todos):
            offset = int(i * span / max(n - 1, 1)) if n > 1 else 0
            due = week_start + timedelta(days=offset)
            if due > deadline:
                due = deadline
            updated_todos.append(todo.model_copy(update={"due_date": due}))

        updated.append(milestone.model_copy(update={"todos": updated_todos}))

    return {"milestones": updated}
