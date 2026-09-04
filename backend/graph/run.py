"""
backend/graph/run.py

CLI harness for the SevaMithra LangGraph orchestrator.

Usage:
    python -m backend.graph.run "user input string here"
"""

import sys
import uuid

from backend.graph.builder import build_graph
from backend.state import create_initial_state


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python -m backend.graph.run "user input string here"')
        sys.exit(1)

    user_input = sys.argv[1]
    graph = build_graph()
    state = create_initial_state(raw_input=user_input)
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    for event in graph.stream(state, config=config, stream_mode="updates"):
        for node_name, node_update in event.items():
            for step in node_update.get("reasoning_log", []):
                print(f"[{step['agent']}] {step['action']}: {step['detail']}")

    result_state = graph.get_state(config).values

    print()
    print(f"thread_id: {thread_id}")
    print(f"final phase: {result_state.get('current_phase')}")
    scheme_threads = result_state.get("scheme_threads", {})
    print(f"scheme_threads: {len(scheme_threads)}")
    for scheme_id, thread in scheme_threads.items():
        print(f"  {scheme_id}: {thread.get('phase')}")


if __name__ == "__main__":
    main()
