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

from langsmith import Client, traceable,evaluate
from langsmith.evaluation import evaluate, LangChainStringEvaluator
from langsmith.schemas import Example, Run

from main import app

# Load environment variables
load_dotenv(override=True, dotenv_path=".env")

# Initialize LangSmith client
client = Client(api_key=os.getenv("LANGSMITH_API_KEY"))
PROJECT_NAME = os.getenv("LANGSMITH_PROJECT", "log-analyzer-eval")


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


def contains_evaluator(run: Run, example: Example) -> Dict[str, Any]:
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


def structure_evaluator(run: Run, example: Example) -> Dict[str, Any]:
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


def min_score_evaluator(run: Run, example: Example) -> Dict[str, Any]:
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


def run_evaluation():
    """
    Run the evaluation experiment using LangSmith SDK.
    """
    print(f"🚀 Starting LangSmith evaluation for project: {PROJECT_NAME}")
    print("=" * 60)
    
    # Load dataset
    dataset = load_evaluation_dataset()
    print(f"📊 Loaded {len(dataset)} test cases")
    
    # Convert dataset to LangSmith examples
    examples = []
    for i, item in enumerate(dataset):
        example = Example(
            inputs=item["inputs"],
            outputs=item["outputs"],
            metadata=item.get("metadata", {})
        )
        examples.append(example)
    
    # Create or get dataset in LangSmith
    dataset_name = f"{PROJECT_NAME}-dataset"
    try:
        # Try to get existing dataset
        existing_dataset = client.read_dataset(dataset_name=dataset_name)
        print(f"📁 Using existing dataset: {dataset_name}")
        # Clear existing examples to avoid duplicates (optional - comment out to keep existing)
        # client.delete_examples(dataset_name=dataset_name)
    except Exception:
        # Create new dataset
        try:
            dataset_id = client.create_dataset(
                dataset_name=dataset_name,
                description="Log analyzer agent evaluation dataset"
            )
            print(f"📁 Created new dataset: {dataset_name}")
        except Exception as e:
            print(f"⚠️  Dataset creation issue (may already exist): {e}")
    
    # Upload examples to dataset
    try:
        client.create_examples(
            inputs=[ex.inputs for ex in examples],
            outputs=[ex.outputs for ex in examples],
            dataset_name=dataset_name
        )
        print(f"✅ Uploaded {len(examples)} examples to dataset")
    except Exception as e:
        print(f"⚠️  Example upload issue (may already exist): {e}")
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
        experiment_prefix=f"{PROJECT_NAME}-experiment",
        max_concurrency=1,  # Run sequentially to avoid rate limits
        verbose=True,
    )
    
    print("\n" + "=" * 60)
    print("📈 Evaluation Results Summary")
    print("=" * 60)
    
    # Print summary statistics
    if results:
        print(f"\n✅ Evaluation completed!")
        print(f"📊 View results in LangSmith UI:")
        print(f"   https://smith.langchain.com/projects/{PROJECT_NAME}")
        print(f"\n💡 To view detailed results, check the LangSmith dashboard.")
    else:
        print("⚠️  No results returned from evaluation")


if __name__ == "__main__":
    # Validate API key
    if not os.getenv("LANGSMITH_API_KEY"):
        raise ValueError(
            "LANGSMITH_API_KEY not found. Please set it in your .env file."
        )
    
    run_evaluation()
