# Log Analyzer Agent

A LangChain/LangGraph-based AI agent that analyzes log files using OpenAI's GPT-4 model. The agent can read log files and provide insights about errors, patterns, or issues.

## Features

- Reads and analyzes log files using AI
- Uses LangGraph for agent orchestration
- Configurable via environment variables
- LangSmith integration for tracing and monitoring

## Prerequisites

- Python 3.8 or higher
- OpenAI API key
- LangSmith API key (optional, for tracing)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd agentic_ai
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cd log_analyzer
cp .env.example .env
```

4. Edit `.env` and add your API keys:
```env
OPENAI_API_KEY="your-openai-api-key-here"
LANGSMITH_API_KEY="your-langsmith-api-key-here"
LANGSMITH_PROJECT="log-analyzer"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"
LOG_DIRECTORY=/langchain/log_analyzer/
```

## Usage

Run the agent from the `log_analyzer` directory:

```bash
cd log_analyzer
python build_exec.py
```

By default, the agent will analyze the `server.log` file located in the `log_analyzer` directory (relative to the script location).

### Log File Paths

The agent uses a configurable log directory system:

- **Default behavior**: The `build_exec.py` script uses `server.log` relative to the script's directory (`log_analyzer/server.log`)
- **Log directory configuration**: The `read_log_file` tool uses the `LOG_DIRECTORY` environment variable (defaults to `./logs`)
- **Path resolution**: 
  - In `build_exec.py`: Log paths are resolved relative to the script location using `Path(__file__).parent`
  - In `log_reader.py`: Log files are read from the `LOG_DIRECTORY` environment variable

To analyze a different log file, you can:
1. Place your log file in the `log_analyzer` directory and update the path in `build_exec.py`
2. Set the `LOG_DIRECTORY` environment variable and use the `read_log_file` tool with just the filename

Example:
```bash
export LOG_DIRECTORY="/path/to/your/logs"
python build_exec.py
```

## Project Structure

```
log_analyzer/
├── agent_state.py      # Defines the agent state structure
├── build_exec.py       # Main execution file with LangGraph workflow
├── log_reader.py      # Tool for reading log files (supports LOG_DIRECTORY)
├── openai_model.py    # OpenAI model configuration
├── server.log         # Sample log file (default analyzed file)
├── .env              # Environment variables (not in git)
└── .env.example      # Environment variable template
```

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `LANGSMITH_API_KEY`: Your LangSmith API key (optional)
- `LANGSMITH_PROJECT`: LangSmith project name (optional)
- `USER_AGENT`: User agent string (optional)
- `LANGSMITH_TRACING`: Set to "true" to enable tracing (set automatically)
- `LOG_DIRECTORY`: Directory path for log files (defaults to `./logs`). Used by the `read_log_file` tool.

## How It Works

1. The agent receives a user query about log files
2. It uses the `read_log_file` tool to read log files from the configured directory
3. The AI model analyzes the logs and provides insights
4. The agent can make multiple tool calls if needed
5. Final response is returned to the user

## Recent Changes

### Security & Configuration Fixes
- ✅ **Fixed environment variable loading**: Environment variables are now loaded from `.env` file before being accessed
- ✅ **API key security**: Created `.env.example` template; `.env` file is properly ignored by git
- ✅ **Safe attribute access**: Improved error handling for tool calls using `getattr()` instead of direct attribute access

### Code Quality Improvements
- ✅ **Module execution**: Main code is now wrapped in `if __name__ == "__main__":` block for proper module behavior
- ✅ **Path handling**: Log file paths are now resolved relative to script location using `Path(__file__).parent` for more reliable path resolution
- ✅ **Dependency management**: Added `requirements.txt` with all project dependencies

### Log Reading Enhancements
- ✅ **Configurable log directory**: Added `LOG_DIRECTORY` environment variable support
- ✅ **Efficient file reading**: Improved log file reading with better memory management
- ✅ **File encoding**: Explicit UTF-8 encoding with error handling

## License

[Add your license here]
