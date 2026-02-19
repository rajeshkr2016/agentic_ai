# Future Features & Improvements

## Features

- [ ] **CLI interface** – Add argparse/click for custom queries, log path, and output format
- [ ] **Interactive mode** – REPL or chat-style interface for multi-turn log analysis
- [ ] **Log pattern detection** – Pre-defined patterns for common errors (HTTP 5xx, tracebacks, OOM)
- [ ] **Export reports** – Save analysis summaries to JSON, Markdown, or HTML
- [ ] **Multi-file correlation** – Correlate events across multiple log files by timestamp
- [ ] **Real-time monitoring** – Tail log files and analyze new entries as they arrive
- [ ] **Slack/Teams integration** – Post critical findings to messaging channels
- [ ] **Elasticsearch integration** - Integrate with ELK and read from an index or so

## Improvements

- [x] **LangSmith Evaluation** – SDK and UI evaluation framework with realistic test cases ✅
- [ ] **Unit tests** – Pytest for tools (list_log_files, read_log_file) and workflow routing
- [ ] **Integration tests** – End-to-end runs with mock log files
- [ ] **Memory-efficient reading** – Tail large logs without loading entire file (e.g., seek from end)
- [ ] **Path validation** – Restrict log paths to LOG_DIRECTORY to prevent path traversal
- [ ] **Structured logging** – Use Python logging instead of print for execution output
- [ ] **Configuration module** – Centralize settings (e.g., pydantic) instead of scattered os.getenv
- [ ] **Error handling** – Retry logic for API calls, clearer errors when tools fail
- [ ] **Streaming output** – Stream final summary token-by-token for faster feedback

## Technical Debt

- [ ] Add type hints for `call_model`, `router`, `summarize_results`
- [ ] Document routing logic (Traceback heuristic) in README
- [ ] Consider moving `load_dotenv` to a single bootstrap point
- [ ] Add `py.typed` if publishing as a library
