import os
from pathlib import Path
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from openai_model import model, tool_node
from dotenv import load_dotenv


class AgentState(TypedDict):
    """State with messages annotated for appending rather than overwriting."""
    messages: Annotated[Sequence[BaseMessage], add_messages]

# Load environment variables from .env file first
load_dotenv(override=True, dotenv_path=".env")

# Set LangSmith tracing (not in .env by default)
os.environ["LANGSMITH_TRACING"] = "true"

def call_model(state: AgentState):
    response = model.invoke(state["messages"])
    return {"messages": [response]}

# Define the graph logic
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

# Add edges: agent can call tools, tools return to agent
workflow.add_edge(START, "agent")
# Safely check for tool_calls attribute
workflow.add_conditional_edges(
    "agent",
    lambda x: "tools" if getattr(x["messages"][-1], "tool_calls", None) else END
)
workflow.add_edge("tools", "agent")

app = workflow.compile()


def main():
    """Main entry point for the log analyzer agent."""
    # Use path relative to script location
    script_dir = Path(__file__).parent
    log_file = script_dir / "server.log"
    
    inputs = {
        "messages": [
            ("user", f"Check the logs at '{log_file}' and tell me if there are any errors.")
        ]
    }
    
    for output in app.stream(inputs):
        print(output)


if __name__ == "__main__":
    main()
