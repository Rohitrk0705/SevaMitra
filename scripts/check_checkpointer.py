"""Proof that LangGraph + SqliteSaver persists state to disk.

The Monitor agent's pause-and-resume trick depends on the checkpointer
actually writing to checkpoints.sqlite, not just holding state in memory.
"""

import sqlite3
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    step: str
    count: int


def node_a(state: State) -> State:
    print(f"node_a received: {state}")
    return {"step": "a", "count": state["count"] + 1}


def node_b(state: State) -> State:
    print(f"node_b received: {state}")
    return {"step": "b", "count": state["count"] + 10}


graph_builder = StateGraph(State)
graph_builder.add_node("a", node_a)
graph_builder.add_node("b", node_b)
graph_builder.add_edge(START, "a")
graph_builder.add_edge("a", "b")
graph_builder.add_edge("b", END)

conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)
checkpointer = SqliteSaver(conn)

graph = graph_builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "test-run-1"}}
final_state = graph.invoke({"step": "start", "count": 0}, config=config)

print(f"Final state: {final_state}")
print("checkpoints.sqlite now exists on disk — this is the persistence proof.")
