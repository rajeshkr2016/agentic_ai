import os
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from log_reader import read_log_file, list_log_files
from dotenv import load_dotenv

# Load environment variables - MUST come before ChatOpenAI()
load_dotenv(override=True, dotenv_path=".env")

# Validate API key
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError(
        "OPENAI_API_KEY not found. Please set it in your .env file or environment variables."
    )

# Get model name from environment or use default
model_name = os.getenv("OPENAI_MODEL", "gpt-5-mini")

# Register all available tools
tools = [read_log_file, list_log_files]

# Create model with tools
model = ChatOpenAI(model=model_name).bind_tools(tools)
tool_node = ToolNode(tools)
