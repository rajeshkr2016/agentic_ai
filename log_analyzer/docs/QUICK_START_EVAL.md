# Quick Start: LangSmith Evaluation

## Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your LANGSMITH_API_KEY
```

## Run SDK Evaluation (5 minutes)

```bash
# Run evaluation script
python evaluate.py
```

This will:
1. Load test cases from `evaluation_dataset.json`
2. Create/update dataset in LangSmith
3. Run agent on all test cases
4. Evaluate responses with custom evaluators
5. Show results summary

## View Results

After running, visit:
```
https://smith.langchain.com/projects/log-analyzer-eval
```

## Test Cases Included

- ✅ Error detection (easy)
- ✅ HTTP 5xx errors (medium)
- ✅ Authentication failures (medium)
- ✅ Critical issues summary (hard)
- ✅ Python tracebacks (medium)
- ✅ Traffic analytics (hard)

## Next Steps

1. **Review Results**: Check LangSmith UI for detailed traces
2. **Debug Failures**: Use trace viewer to see what went wrong
3. **Improve Agent**: Update prompts/routing based on failures
4. **Re-run**: Compare new results with baseline
5. **Add Cases**: Extend `evaluation_dataset.json` with your own tests

## Common Issues

**"LANGSMITH_API_KEY not found"**
- Check `.env` file has `LANGSMITH_API_KEY=your-key`

**"No logs found"**
- Ensure `LOG_DIRECTORY` points to directory with `.log` files
- Default is `./logs` (sample logs included)

**"Evaluation failed"**
- Check LangSmith UI for error details
- Verify API key has correct permissions
- Check network connectivity

For detailed instructions, see [EVALUATION.md](EVALUATION.md)
