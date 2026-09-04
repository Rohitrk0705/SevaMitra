"""
backend/graph/builder.py

Compiles the SevaMithra LangGraph orchestrator: 6 nodes, 2 conditional
edges, checkpointed via SqliteSaver at backend/graph/checkpoints.sqlite
(a separate file from the Rung 2 toy checkpoints.sqlite at the repo root).
"""

import sqlite3
from pathlib import Path
from typing import Optional

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from backend.graph.edges import should_escalate, should_verify
from backend.graph.nodes import (
    discovery_node,
    escalate_node,
    execution_node,
    monitor_node,
    trigger_node,
    verification_node,
)
from backend.state import SevaState

CHECKPOINT_DB_PATH = Path(__file__).resolve().parent / "checkpoints.sqlite"


def build_graph(interrupt_before: Optional[list] = None) -> CompiledStateGraph:
    """Builds and compiles the SevaMithra state graph with its SqliteSaver checkpointer.

    interrupt_before is the seam the real Monitor Agent (Rung 10) will use
    to pause the graph mid-run — passing e.g. ["monitor"] here makes the
    compiled graph stop right before that node, leaving a resumable
    checkpoint on disk.
    """
    graph_builder = StateGraph(SevaState)

    graph_builder.add_node("trigger", trigger_node)
    graph_builder.add_node("discovery", discovery_node)
    graph_builder.add_node("verification", verification_node)
    graph_builder.add_node("execution", execution_node)
    graph_builder.add_node("monitor", monitor_node)
    graph_builder.add_node("escalate", escalate_node)

    graph_builder.add_edge(START, "trigger")
    graph_builder.add_edge("trigger", "discovery")
    graph_builder.add_conditional_edges(
        "discovery",
        should_verify,
        {"verification": "verification", "end": END},
    )
    graph_builder.add_edge("verification", "execution")
    graph_builder.add_edge("execution", "monitor")
    graph_builder.add_conditional_edges(
        "monitor",
        should_escalate,
        {"escalate": "escalate", "end": END},
    )
    graph_builder.add_edge("escalate", END)

    conn = sqlite3.connect(str(CHECKPOINT_DB_PATH), check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    return graph_builder.compile(checkpointer=checkpointer, interrupt_before=interrupt_before)
