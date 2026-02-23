import os
from pathlib import Path
from typing import Annotated, Sequence, TypedDict, Literal
from dotenv import load_dotenv

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langsmith import traceable
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from model.model_loader import load_model
from tools.log_reader import read_log_file, list_log_files

tools = [read_log_file, list_log_files]
model, tool_node = load_model(tools)

from upload_to_langsmith import upload_logs_to_langsmith

# 1. Configuration & State
load_dotenv(override=True)
os.environ["LANGSMITH_TRACING"] = "true"

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

def _current_temperature() -> str:
    """
    Resolve the effective temperature for logging.
    Prefer runtime env overrides used by evaluation script.
    """
    temp = os.getenv("OPENAI_TEMPERATURE") or os.getenv("LLM_TEMPERATURE")
    return temp if temp not in (None, "") else "default"


def _log_startup_banner(entrypoint: str) -> None:
    """Print a single startup line when a process begins. Called once per run."""
    log_dir = os.getenv("LOG_DIRECTORY", "./logs")
    provider = os.getenv("LLM_PROVIDER", "openai")
    model_name = os.getenv("MODEL_NAME", "(default)")
    temperature = _current_temperature()
    print(
        f"[{entrypoint}] "
        f"provider={provider} model={model_name} "
        f"temperature={temperature} log_dir={log_dir}"
    )

SYSTEM_PROMPT = SystemMessage(content=(
    "You are a log analysis agent. Your job is to read log files using the "
    "tools available and report ONLY what you actually find in them.\n"
    "Rules:\n"
    "- Never fabricate errors, tracebacks, or timestamps that are not in the logs.\n"
    "- If the logs do not contain what the user asked for, say so explicitly.\n"
    "- Always call list_log_files first, then read the relevant files."
))

# 2. Nodes
@traceable(run_type="llm")
def call_model(state: AgentState):
    """The 'Brain' - decides which logs to read."""
    messages = list(state["messages"])
    # Prepend system prompt if not already present
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SYSTEM_PROMPT] + messages
    response = model.invoke(messages)
    return {"messages": [response]}

def summarize_results(state: AgentState):
    """The 'Synthesizer' - converts raw log data into a clean report."""
    summary_prompt = HumanMessage(content=(
        "You have finished reading the logs. Provide a structured log analysis summary "
        "using EXACTLY this markdown format:\n\n"
        "### Conclusion\n"
        "<one-sentence overall finding>\n\n"
        "### 1. Root Cause\n"
        "<description>\n\n"
        "### 2. Timestamp\n"
        "<first and last relevant timestamp>\n\n"
        "### 3. Suggested Fix\n"
        "<actionable recommendation>\n\n"
        "Do not add any text before '### Conclusion'."
    ))
    # We pass the full history to the model for the final summary
    response = model.invoke(state["messages"] + [summary_prompt])
    return {"messages": [response]}

# 3. Routing Logic (The Conditional Edge)
@traceable
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
    _log_startup_banner("main")
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
    
    # # Optional: Upload logs to LangSmith if function is available
    # if upload_logs_to_langsmith:
    #     upload_logs_to_langsmith("log-analyzer", log_dir)
