import os
from pathlib import Path
from typing import Annotated, Sequence, TypedDict, Literal
from dotenv import load_dotenv

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from openai_model import model, tool_node

# 1. Configuration & State
load_dotenv(override=True)
os.environ["LANGSMITH_TRACING"] = "true"

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# 2. Nodes
def call_model(state: AgentState):
    """The 'Brain' - decides which logs to read."""
    response = model.invoke(state["messages"])
    return {"messages": [response]}

def summarize_results(state: AgentState):
    """The 'Synthesizer' - converts raw log data into a clean report."""
    summary_prompt = HumanMessage(content=(
        "You have finished reading the logs. Provide a structured 'Log Analysis Summary' "
        "including: 1. Root Cause, 2. Timestamp, and 3. Suggested Fix."
    ))
    # We pass the full history to the model for the final summary
    response = model.invoke(state["messages"] + [summary_prompt])
    return {"messages": [response]}

# 3. Routing Logic (The Conditional Edge)
def router(state: AgentState) -> Literal["tools", "summarize", "agent"]:
    last_msg = state["messages"][-1]
    
    # Path A: Model wants to use a tool (list_dir, read_file)
    if getattr(last_msg, "tool_calls", None):
        return "tools"
    
    # Path B: Detect if we found a crash but might need more context (Stack Trace)
    # If 'Traceback' is in the text, we let the agent loop once more to get detail
    if "Traceback" in last_msg.content and len(state["messages"]) < 6:
        return "agent"
    
    # Path C: Information gathered, move to summary
    return "summarize"

# 4. Graph Construction
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_node("summarize", summarize_results)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", router)
workflow.add_edge("tools", "agent")
workflow.add_edge("summarize", END)

app = workflow.compile()

# 5. Main Execution
if __name__ == "__main__":
    log_dir = os.getenv("LOG_DIRECTORY", "./logs")
    
    inputs = {
        "messages": [
            ("user", f"Analyze the logs in '{log_dir}'. Identify any recurring crashes.")
        ]
    }
    
    for output in app.stream(inputs, stream_mode="updates"):
        for node, data in output.items():
            print(f"--- Node: {node} ---")
            print(data["messages"][-1].content or "Calling Tools...")
