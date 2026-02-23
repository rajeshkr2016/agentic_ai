from collections import deque
from langchain_core.tools import tool
from pathlib import Path
from typing import List
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv(override=True, dotenv_path=".env")

# Retrieve the directory from environment variables
LOG_DIR = os.getenv("LOG_DIRECTORY", "./logs")

@tool
def list_log_files() -> List[str]:
    """Lists all .log files in the configured log directory."""
    try:
        path = Path(LOG_DIR)
        if not path.is_dir():
            return [f"Error: {LOG_DIR} is not a valid directory."]
        
        return [f.name for f in path.glob("*.log")]
    except Exception as e:
        return [f"Error listing logs: {str(e)}"]

@tool
def read_log_file(filename: str, last_n_lines: int = 20) -> str:
    """
    Reads the last N lines of a specific log file from the log directory.
    Only the filename (e.g., 'server.log') is required.
    """
    try:
        # Join the base LOG_DIR with the filename for security
        path = Path(LOG_DIR) / filename
        
        if not path.exists():
            return f"Error: File {filename} not found in {LOG_DIR}"

        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return "".join(deque(f, maxlen=last_n_lines))
            
    except Exception as e:
        return f"Error reading log: {str(e)}"
