from langgraph.graph import StateGraph, END

from app.agent.state import RescheduleState
from app.agent.nodes.analyze_progress import analyze_progress_node
from app.agent.nodes.smart_reschedule import smart_reschedule_node


def _build():
    graph = StateGraph(RescheduleState)
    graph.add_node("analyze_progress", analyze_progress_node)
    graph.add_node("smart_reschedule", smart_reschedule_node)
    
    graph.set_entry_point("analyze_progress")
    graph.add_edge("analyze_progress", "smart_reschedule")
    graph.add_edge("smart_reschedule", END)
    
    return graph.compile()


reschedule_pipeline = _build()
