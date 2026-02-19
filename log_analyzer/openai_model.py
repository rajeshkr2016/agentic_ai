from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from log_reader import read_log_file
from dotenv import load_dotenv
# This MUST come before ChatOpenAI()
load_dotenv(override=True, dotenv_path=".env")

# ISSUE: Hardcoded model name "gpt-4" - should be configurable via environment variable
# ISSUE: No error handling if API key is missing - ChatOpenAI will fail at runtime
tools = [read_log_file]
model = ChatOpenAI(model="gpt-5-mini").bind_tools(tools)
tool_node = ToolNode(tools)
