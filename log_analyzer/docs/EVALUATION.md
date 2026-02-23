# LangSmith Evaluation Guide

This guide explains how to evaluate the log analyzer agent using both the LangSmith UI and SDK.

## Prerequisites

1. **LangSmith Account**: Sign up at https://smith.langchain.com
2. **API Key**: Get your API key from LangSmith settings
3. **Environment Setup**: Ensure `.env` has `LANGSMITH_API_KEY` and `LANGSMITH_PROJECT`

## Method 1: LangSmith UI Evaluation

### Step 1: Upload Dataset

1. Go to https://smith.langchain.com
2. Navigate to **Datasets** → **Create Dataset**
3. Upload `evaluation_dataset.json` or create manually:
   - Name: `log-analyzer-eval-dataset`
   - Add examples from `evaluation_dataset.json`

### Step 2: Create Evaluation Run

1. Go to **Experiments** → **New Experiment**
2. Configure:
   - **Dataset**: Select `log-analyzer-eval-dataset`
   - **Model/Agent**: Your log analyzer agent
   - **Evaluators**: 
     - Contains Check (custom)
     - Structure Check (custom)
     - Min Score Check (custom)

### Step 3: Run Evaluation

1. Click **Run Experiment**
2. Monitor progress in real-time
3. View results:
   - Pass/fail rates
   - Score distributions
   - Individual test case results
   - Comparison across runs

### Step 4: Analyze Results

- **Dashboard**: Overview of all metrics
- **Details**: Click individual runs to see inputs/outputs
- **Compare**: Compare different agent versions
- **Export**: Download results as CSV/JSON

## Method 2: SDK Evaluation (Programmatic)

### Quick Start

```bash
# Run evaluation script
python evaluate.py
```

### What It Does

1. **Loads Dataset**: Reads `evaluation_dataset.json`
2. **Creates Dataset**: Uploads to LangSmith (or uses existing)
3. **Runs Agent**: Executes each test case through the agent
4. **Evaluates**: Applies custom evaluators:
   - **Contains Check**: Verifies expected keywords in output
   - **Structure Check**: Validates expected structure elements
   - **Min Score Check**: Ensures score meets threshold
5. **Reports**: Prints summary and provides LangSmith UI link

### Custom Evaluators

The evaluation uses three custom evaluators:

#### 1. Contains Evaluator
Checks if output contains expected keywords:
```python
expected_contains: ["error", "crash", "exception"]
```

#### 2. Structure Evaluator
Validates output has expected structure:
```python
expected_structure: ["root cause", "timestamp", "suggested fix"]
```

#### 3. Min Score Evaluator
Ensures overall score meets minimum threshold:
```python
min_score: 0.7  # Must score at least 70%
```

### Evaluation Dataset Format

Each test case in `evaluation_dataset.json` has:

```json
{
  "inputs": {
    "query": "Your test query here"
  },
  "outputs": {
    "expected_contains": ["keyword1", "keyword2"],
    "expected_structure": ["element1", "element2"],
    "min_score": 0.7
  },
  "metadata": {
    "difficulty": "easy|medium|hard",
    "category": "error_detection|security|analytics"
  }
}
```

## Adding New Test Cases

Edit `evaluation_dataset.json` to add new test cases:

```json
{
  "inputs": {
    "query": "Your new test query"
  },
  "outputs": {
    "expected_contains": ["expected", "keywords"],
    "expected_structure": ["required", "elements"],
    "min_score": 0.75
  },
  "metadata": {
    "difficulty": "medium",
    "category": "your_category"
  }
}
```

## Debugging Failed Tests

### Common Issues

1. **Agent doesn't use tools**
   - Check tool registration in `openai_model.py`
   - Verify tools are bound to model

2. **Output format mismatch**
   - Adjust `expected_structure` in dataset
   - Check agent's summary prompt in `main.py`

3. **Low scores**
   - Review agent responses in LangSmith UI
   - Adjust prompts or routing logic
   - Add more context to queries

### Viewing Traces

1. Go to LangSmith UI → **Traces**
2. Filter by your project
3. Click any trace to see:
   - Full conversation flow
   - Tool calls and responses
   - Timing information
   - Error messages

## Continuous Improvement Workflow

1. **Run Evaluation**: `python evaluate.py`
2. **Review Results**: Check LangSmith UI
3. **Identify Issues**: Find failing test cases
4. **Debug**: Use trace viewer to understand failures
5. **Fix**: Update agent code (prompts, routing, tools)
6. **Re-run**: Compare new results with baseline
7. **Iterate**: Repeat until scores improve

## Metrics to Track

- **Pass Rate**: % of tests passing
- **Average Score**: Mean score across all tests
- **Category Performance**: Scores by category (error_detection, security, etc.)
- **Difficulty Performance**: Scores by difficulty (easy, medium, hard)
- **Response Time**: How long each query takes
- **Tool Usage**: How often tools are called correctly

## Best Practices

1. **Start Small**: Begin with easy test cases
2. **Add Gradually**: Add harder cases as agent improves
3. **Realistic Queries**: Use queries similar to real user questions
4. **Regular Evaluation**: Run evaluations after each change
5. **Compare Versions**: Track improvements over time
6. **Document Changes**: Note what changed between evaluations

## Troubleshooting

### SDK Errors

```bash
# Check API key
echo $LANGSMITH_API_KEY

# Verify project name
grep LANGSMITH_PROJECT .env

# Test connection
python -c "from langsmith import Client; print(Client().list_projects())"
```

### UI Issues

- Clear browser cache
- Check API key permissions
- Verify dataset exists
- Ensure project name matches

## Next Steps

- Add more test cases to `evaluation_dataset.json`
- Create category-specific evaluators
- Set up CI/CD integration for automated evaluation
- Compare different model versions
- Track performance over time
