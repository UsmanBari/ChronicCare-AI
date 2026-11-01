# Orchestrator package for ChronicCare AI check-in completion pipeline
from orchestrator.state import CheckinState

__all__ = [
    "CheckinState",
    "checkin_graph",
    "run_checkin_graph",
    "run_checkin_graph_with_state",
]


def __getattr__(name: str):
    if name in ("checkin_graph", "run_checkin_graph", "run_checkin_graph_with_state"):
        import orchestrator.graph as _graph

        return getattr(_graph, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

