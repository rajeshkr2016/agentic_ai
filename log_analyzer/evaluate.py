"""
LangSmith SDK Evaluation Script

This script runs programmatic evaluations of the log analyzer agent using LangSmith SDK.
It tests the agent against a dataset of realistic queries and evaluates the responses.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv

from langsmith import Client, traceable
from langsmith.evaluation import evaluate
from langsmith.schemas import Run

from main import app

# Load environment variables
load_dotenv(override=True, dotenv_path=".env")

# Initialize LangSmith client
client = Client(api_key=os.getenv("LANGSMITH_API_KEY"))
PROJECT_NAME = os.getenv("LANGSMITH_PROJECT", "log-analyzer")


def load_evaluation_dataset() -> List[Dict[str, Any]]:
    """Load evaluation dataset from JSON file."""
    dataset_path = Path(__file__).parent / "evaluation_dataset.json"
    with open(dataset_path, "r") as f:
        return json.load(f)


@traceable(name="log_analyzer_agent")
def run_agent(query: str) -> Dict[str, Any]:
    """
    Run the agent with a given query and return the final response.
    This is wrapped with @traceable for LangSmith tracking.
    """
    from langchain_core.messages import HumanMessage
    
    log_dir = os.getenv("LOG_DIRECTORY", "./logs")
    
    inputs = {
        "messages": [
            HumanMessage(content=query)
        ]
    }
    
    # Collect all messages from the stream
    final_messages = []
    for output in app.stream(inputs, stream_mode="updates"):
        for node, data in output.items():
            if "messages" in data and data["messages"]:
                final_messages.extend(data["messages"])
    
    # Get the last message content (final response)
    if final_messages:
        last_message = final_messages[-1]
        if hasattr(last_message, "content"):
            return {"output": last_message.content}
        else:
            return {"output": str(last_message)}
    
    return {"output": "No response generated"}


def agent_predict(inputs: Dict[str, str]) -> Dict[str, str]:
    """
    Wrapper function for the agent that LangSmith can evaluate.
    This is the function that gets called during evaluation.
    """
    query = inputs.get("query", "")
    result = run_agent(query)
    return {"output": result.get("output", "")}


def contains_evaluator(run: Run, example) -> Dict[str, Any]:
    """
    Custom evaluator that checks if the output contains expected keywords.
    """
    prediction = run.outputs.get("output", "").lower()
    expected = example.outputs.get("expected_contains", [])
    
    if not expected:
        return {"key": "contains_check", "score": 1.0}
    
    found_count = sum(1 for keyword in expected if keyword.lower() in prediction)
    score = found_count / len(expected) if expected else 0.0
    
    return {
        "key": "contains_check",
        "score": score,
        "comment": f"Found {found_count}/{len(expected)} expected keywords"
    }


def structure_evaluator(run: Run, example) -> Dict[str, Any]:
    """
    Custom evaluator that checks if the output has expected structure elements.
    """
    prediction = run.outputs.get("output", "").lower()
    expected_structure = example.outputs.get("expected_structure", [])
    
    if not expected_structure:
        return {"key": "structure_check", "score": 1.0}
    
    found_count = sum(1 for element in expected_structure if element.lower() in prediction)
    score = found_count / len(expected_structure) if expected_structure else 0.0
    
    return {
        "key": "structure_check",
        "score": score,
        "comment": f"Found {found_count}/{len(expected_structure)} expected structure elements"
    }


def min_score_evaluator(run: Run, example) -> Dict[str, Any]:
    """
    Evaluator that checks if the overall score meets the minimum threshold.
    """
    min_score = example.outputs.get("min_score", 0.7)
    
    # Calculate average of other evaluators
    contains_score = contains_evaluator(run, example).get("score", 0.0)
    structure_score = structure_evaluator(run, example).get("score", 0.0)
    avg_score = (contains_score + structure_score) / 2
    
    passed = avg_score >= min_score
    
    return {
        "key": "min_score_check",
        "score": 1.0 if passed else 0.0,
        "comment": f"Average score {avg_score:.2f} {'meets' if passed else 'below'} minimum {min_score}"
    }


def run_evaluation(project_name: str = None, project_url: str = None):
    """
    Run the evaluation experiment using LangSmith SDK.
    
    Args:
        project_name: LangSmith project name. If not provided, uses LANGSMITH_PROJECT env var.
        project_url: LangSmith project URL. If not provided, constructs from project_name.
    """
    if project_name is None:
        project_name = os.getenv("LANGSMITH_PROJECT", "log-analyzer")
    
    if project_url is None:
        project_url = f"https://smith.langchain.com/projects/{project_name}"
    
    print(f"🚀 Starting LangSmith evaluation for project: {project_name}")
    print("=" * 60)
    
    # Load dataset
    dataset = load_evaluation_dataset()
    print(f"📊 Loaded {len(dataset)} test cases")
    
    # Create or get dataset in LangSmith
    dataset_name = f"{project_name}-dataset"
    try:
        # Try to get existing dataset
        client.read_dataset(dataset_name=dataset_name)
        print(f"📁 Using existing dataset: {dataset_name}")
    except Exception:
        # Create new dataset
        try:
            client.create_dataset(
                dataset_name=dataset_name,
                description="Log analyzer agent evaluation dataset"
            )
            print(f"📁 Created new dataset: {dataset_name}")
        except Exception as e:
            print(f"⚠️  Dataset creation issue (may already exist): {e}")
    
    # Upload examples only if the dataset is empty (avoid duplicates on re-runs)
    existing_examples = list(client.list_examples(dataset_name=dataset_name))
    if existing_examples:
        print(f"⏭️  Skipping upload — {len(existing_examples)} examples already exist in dataset")
    else:
        try:
            client.create_examples(
                inputs=[item["inputs"] for item in dataset],
                outputs=[item["outputs"] for item in dataset],
                dataset_name=dataset_name
            )
            print(f"✅ Uploaded {len(dataset)} examples to dataset")
        except Exception as e:
            print(f"⚠️  Example upload issue: {e}")
            print(f"   Continuing with existing examples...")
    
    # Run evaluation
    print("\n🔍 Running evaluation...")
    print("-" * 60)
    
    results = evaluate(
        agent_predict,
        data=dataset_name,
        evaluators=[
            contains_evaluator,
            structure_evaluator,
            min_score_evaluator,
        ],
        experiment_prefix=f"{project_name}-experiment",
        max_concurrency=1,  # Run sequentially to avoid rate limits
    )
    
    print("\n" + "=" * 60)
    print("📈 Evaluation Results Summary")
    print("=" * 60)
    
    # Wait for experiment feedback to be processed so we can read results
    results.wait()
    
    # Get the correct experiment URL directly from results.experiment_name
    results_url = project_url  # fallback
    try:
        experiment_name = results.experiment_name
        experiment_project = client.read_project(project_name=experiment_name)
        experiment_url = getattr(experiment_project, 'url', None)
        if experiment_url:
            results_url = experiment_url
        else:
            # Construct URL from dataset id + experiment id
            dataset = client.read_dataset(dataset_name=dataset_name)
            results_url = (
                f"https://smith.langchain.com/o/~/datasets/{dataset.id}/compare"
                f"?selectedSessions={experiment_project.id}"
            )
    except Exception:
        pass
    
    # Aggregate scores by evaluator key
    scores_by_key: Dict[str, List[float]] = {}
    n_results = 0
    for row in results:
        n_results += 1
        eval_results = getattr(row, "evaluation_results", None)
        if eval_results is None:
            continue
        res_list = getattr(eval_results, "results", [])
        for r in res_list or []:
            key = getattr(r, "key", "unknown")
            score = getattr(r, "score", None)
            if score is not None and isinstance(score, (int, float)):
                scores_by_key.setdefault(key, []).append(float(score))
    
    if not scores_by_key and n_results == 0:
        print("\n⚠️  No evaluation results found. Results may still be processing.")
        print("   Check the LangSmith UI in a minute for full feedback.")
    else:
        print(f"\n✅ Evaluation completed ({n_results} runs)")
        if scores_by_key:
            print("\n  Evaluator scores (average):")
            for key in sorted(scores_by_key.keys()):
                vals = scores_by_key[key]
                avg = sum(vals) / len(vals) if vals else 0
                print(f"    {key}: {avg:.2f}  (n={len(vals)})")
        print(f"\n📊 View full results in LangSmith:")
        print(f"   {results_url}")
    print()


if __name__ == "__main__":
    # Validate API key
    if not os.getenv("LANGSMITH_API_KEY"):
        raise ValueError(
            "LANGSMITH_API_KEY not found. Please set it in your .env file."
        )
    
    run_evaluation()
