"""
LangSmith SDK Evaluation Script

Experiment naming convention:
    {project}-{provider}-{model}-example-{N}

Each example for each model gets its own experiment in LangSmith,
making per-example comparisons across models trivial in the UI.
"""

import os
import json
import argparse
import fcntl
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv

from langsmith import Client, traceable
from langsmith.evaluation import evaluate
from langsmith.schemas import Run

load_dotenv(override=True, dotenv_path=".env")

client = Client(api_key=os.getenv("LANGSMITH_API_KEY"))
PROJECT_NAME = os.getenv("LANGSMITH_PROJECT", "log-analyzer")
_APP = None


# ---------------------------------------------------------------------------
# App loader
# ---------------------------------------------------------------------------

def get_app():
    global _APP
    if _APP is None:
        from main import app as compiled_app
        _APP = compiled_app
    return _APP


def load_evaluation_dataset() -> List[Dict[str, Any]]:
    dataset_path = Path(__file__).parent / "data/evaluation_dataset.json"
    with open(dataset_path, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Agent runner
# ---------------------------------------------------------------------------

@traceable(name="log_analyzer_agent")
def run_agent(query: str) -> Dict[str, Any]:
    from langchain_core.messages import HumanMessage
    inputs = {"messages": [HumanMessage(content=query)]}
    final_messages = []
    app = get_app()
    for output in app.stream(inputs, stream_mode="updates"):
        for node, data in output.items():
            if "messages" in data and data["messages"]:
                final_messages.extend(data["messages"])
    if final_messages:
        last = final_messages[-1]
        return {"output": last.content if hasattr(last, "content") else str(last)}
    return {"output": "No response generated"}


def agent_predict(inputs: Dict[str, str]) -> Dict[str, str]:
    """Called by LangSmith evaluate() for each example. Throttled between calls."""
    import time
    throttle = float(os.getenv("EVAL_THROTTLE_SECONDS", "15"))
    result = run_agent(inputs.get("query", ""))
    print(f"[evaluate] throttling {throttle}s before next example...")
    time.sleep(throttle)
    return {"output": result.get("output", "")}


# ---------------------------------------------------------------------------
# Evaluators
# ---------------------------------------------------------------------------

def contains_evaluator(run: Run, example) -> Dict[str, Any]:
    prediction = run.outputs.get("output", "").lower()
    expected = example.outputs.get("expected_contains", [])
    if not expected:
        return {"key": "contains_check", "score": 1.0}
    found = sum(1 for k in expected if k.lower() in prediction)
    return {
        "key": "contains_check",
        "score": found / len(expected),
        "comment": f"Found {found}/{len(expected)} expected keywords",
    }


def structure_evaluator(run: Run, example) -> Dict[str, Any]:
    prediction = run.outputs.get("output", "").lower()
    expected = example.outputs.get("expected_structure", [])
    if not expected:
        return {"key": "structure_check", "score": 1.0}
    found = sum(1 for e in expected if e.lower() in prediction)
    return {
        "key": "structure_check",
        "score": found / len(expected),
        "comment": f"Found {found}/{len(expected)} expected structure elements",
    }


def min_score_evaluator(run: Run, example) -> Dict[str, Any]:
    min_score = example.outputs.get("min_score", 0.7)
    avg = (
        contains_evaluator(run, example).get("score", 0.0)
        + structure_evaluator(run, example).get("score", 0.0)
    ) / 2
    return {
        "key": "min_score_check",
        "score": 1.0 if avg >= min_score else 0.0,
        "comment": f"Average {avg:.2f} {'meets' if avg >= min_score else 'below'} minimum {min_score}",
    }


def llm_judge_evaluator(run: Run, example) -> Dict[str, Any]:
    from model.model_loader import load_judge_model
    judge_model = os.getenv("JUDGE_MODEL", "llama-3.3-70b-versatile")
    judge_provider = os.getenv("JUDGE_PROVIDER", "groq")
    judge = load_judge_model()

    query = example.inputs.get("query", "")
    output = run.outputs.get("output", "") if run.outputs else ""

    metadata = example.metadata or {}
    category = metadata.get("category", "general")
    difficulty = metadata.get("difficulty", "unknown")

    prompt = f"""You are an impartial judge evaluating a log analysis AI assistant.

IMPORTANT CONTEXT: The agent can only report what is actually present in the logs.
If the logs do not contain what the query asks for, a correct agent response is to
report that finding clearly rather than fabricating results. Do NOT penalise the
agent for the absence of data in the logs — penalise only poor reasoning or an
unhelpful response given what the logs actually contain.

Test category : {category}
Difficulty    : {difficulty}

User query:
{query}

Agent response:
{output}

Score the response from 0 to 10 on these three criteria:
1. Relevance     - does it address the query given what the logs actually contain?
2. Completeness  - does it cover root cause, timestamp, and a fix where applicable?
3. Actionability - is the suggested fix or finding concrete and useful?

Respond with ONLY this format, no extra text:
SCORE: <0-10>
REASON: <one sentence>"""

    try:
        text = judge.invoke(prompt).content.strip()
        score_raw, reason = 0, "Could not parse judge response"
        for line in text.splitlines():
            if line.startswith("SCORE:"):
                score_raw = int(line.split(":", 1)[1].strip())
            elif line.startswith("REASON:"):
                reason = line.split(":", 1)[1].strip()
        score = round(min(max(score_raw, 0), 10) / 10, 2)
        return {"key": "llm_judge", "score": score, "comment": f"[{judge_provider}/{judge_model}] {reason}"}
    except Exception as e:
        return {"key": "llm_judge", "score": 0.0, "comment": f"Judge error: {e}"}


# ---------------------------------------------------------------------------
# Experiment naming — one experiment per model per example
# ---------------------------------------------------------------------------

def _experiment_prefix(project_name: str, example_index: int) -> str:
    """
    Produces: {project}-{provider}-{model}-example-{N}
    e.g.    : log-analyzer-groq-llama-3.3-70b-versatile-example-0
    """
    provider = os.getenv("LLM_PROVIDER", "openai")
    model = os.getenv("MODEL_NAME", "default")
    return f"{project_name}-{provider}-{model}-example-{example_index}"


# ---------------------------------------------------------------------------
# Per-example runner
# ---------------------------------------------------------------------------

def _run_single_example(
    project_name: str,
    project_url: str,
    dataset_name: str,
    examples_ordered: list,
    example_index: int,
    total: int,
) -> None:
    """Run evaluation for one example as its own named experiment."""
    example = examples_ordered[example_index]
    prefix = _experiment_prefix(project_name, example_index)

    print(f"\n{'─' * 60}")
    print(f"🔍 Example #{example_index} of {total - 1}")
    print(f"🏷️  Experiment: {prefix}")
    print(f"   Query: {example.inputs.get('query', '')}")
    print(f"{'─' * 60}")

    results = evaluate(
        agent_predict,
        data=[example],
        evaluators=[
            contains_evaluator,
            structure_evaluator,
            min_score_evaluator,
            llm_judge_evaluator,
        ],
        experiment_prefix=prefix,
        max_concurrency=1,
    )

    results.wait()

    for row in results:
        res_list = getattr(getattr(row, "evaluation_results", None), "results", []) or []
        for r in res_list:
            key = getattr(r, "key", "?")
            score = getattr(r, "score", None)
            comment = getattr(r, "comment", "")
            if score is not None:
                print(f"   {key}: {float(score):.2f}  — {comment}")

    results_url = project_url
    try:
        exp_project = client.read_project(project_name=results.experiment_name)
        url = getattr(exp_project, "url", None)
        if url:
            results_url = url
        else:
            ds = client.read_dataset(dataset_name=dataset_name)
            results_url = (
                f"https://smith.langchain.com/o/~/datasets/{ds.id}/compare"
                f"?selectedSessions={exp_project.id}"
            )
    except Exception:
        pass

    print(f"   📊 {results_url}")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_evaluation(
    project_name: str = None,
    project_url: str = None,
    temperature: float | None = None,
    example_index: int | None = None,
) -> None:
    """
    Acquires a process lock (one experiment at a time), then runs either
    a single example or all examples — each as its own named experiment.
    """
    if temperature is not None:
        os.environ["LLM_TEMPERATURE"] = str(temperature)
        os.environ["OPENAI_TEMPERATURE"] = str(temperature)

    if project_name is None:
        project_name = os.getenv("LANGSMITH_PROJECT", "log-analyzer")
    if project_url is None:
        project_url = f"https://smith.langchain.com/projects/{project_name}"

    from main import _log_startup_banner
    _log_startup_banner("evaluate")

    lock_path = Path("/tmp/log_analyzer_eval.lock")
    lock_file = open(lock_path, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("⛔ Another evaluation is already running.")
        print(f"   Wait for it to finish or delete {lock_path} if it's stale.")
        lock_file.close()
        return

    try:
        _run_evaluation_inner(project_name, project_url, temperature, example_index)
    finally:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()
        lock_path.unlink(missing_ok=True)


def _run_evaluation_inner(
    project_name: str,
    project_url: str,
    temperature: float | None,
    example_index: int | None,
) -> None:
    print(f"🚀 Starting LangSmith evaluation for project: {project_name}")
    if temperature is not None:
        print(f"🌡️  Temperature override: {temperature}")
    print("=" * 60)

    local_dataset = load_evaluation_dataset()
    total = len(local_dataset)

    if example_index is not None and not (0 <= example_index < total):
        raise ValueError(
            f"--example {example_index} is out of range. "
            f"Dataset has {total} examples (0-{total - 1})."
        )

    indices_to_run = [example_index] if example_index is not None else list(range(total))
    print(f"📊 Examples to run: {indices_to_run} (of {total} total)")

    # Ensure dataset exists in LangSmith
    dataset_name = f"{project_name}-dataset"
    try:
        client.read_dataset(dataset_name=dataset_name)
        print(f"📁 Using existing dataset: {dataset_name}")
    except Exception:
        try:
            client.create_dataset(dataset_name=dataset_name, description="Log analyzer agent evaluation dataset")
            print(f"📁 Created new dataset: {dataset_name}")
        except Exception as e:
            print(f"⚠️  Dataset creation issue: {e}")

    # Upload examples if dataset is empty
    existing_examples = list(client.list_examples(dataset_name=dataset_name))
    if existing_examples:
        print(f"⏭️  Skipping upload — {len(existing_examples)} examples already exist")
    else:
        try:
            client.create_examples(
                inputs=[item["inputs"] for item in local_dataset],
                outputs=[item["outputs"] for item in local_dataset],
                dataset_name=dataset_name,
            )
            print(f"✅ Uploaded {total} examples to dataset")
            existing_examples = list(client.list_examples(dataset_name=dataset_name))
        except Exception as e:
            print(f"⚠️  Example upload issue: {e}")

    # Sort by creation time so index 0 always maps to first uploaded example
    examples_ordered = sorted(existing_examples, key=lambda e: e.created_at)

    if not examples_ordered:
        print("❌ No examples found in remote dataset. Cannot run evaluation.")
        return

    if len(examples_ordered) != total:
        print(f"⚠️  Remote dataset has {len(examples_ordered)} examples but local has {total}. Indices may be misaligned.")

    # Run each example as its own experiment, one at a time
    for idx in indices_to_run:
        _run_single_example(
            project_name=project_name,
            project_url=project_url,
            dataset_name=dataset_name,
            examples_ordered=examples_ordered,
            example_index=idx,
            total=total,
        )

    print(f"\n{'=' * 60}")
    print(f"✅ All {len(indices_to_run)} experiment(s) complete.")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run LangSmith evaluation for log analyzer.")
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Model temperature override (e.g., 0.0, 0.5, 1.0).",
    )
    parser.add_argument(
        "--example",
        type=int,
        default=None,
        metavar="INDEX",
        help=(
            "Run a single example by index (0-5) as its own experiment. "
            "Omit to run all examples, each as a separate experiment."
        ),
    )
    parser.add_argument(
        "--provider",
        type=str,
        default=None,
        help="Agent LLM provider, overrides LLM_PROVIDER in .env (e.g. groq, openai, google).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Agent model name, overrides MODEL_NAME in .env (e.g. llama-3.3-70b-versatile).",
    )
    parser.add_argument(
        "--judge-provider",
        type=str,
        default=None,
        dest="judge_provider",
        help="Judge LLM provider, overrides JUDGE_PROVIDER in .env.",
    )
    parser.add_argument(
        "--judge-model",
        type=str,
        default=None,
        dest="judge_model",
        help="Judge model name, overrides JUDGE_MODEL in .env.",
    )
    args = parser.parse_args()

    # CLI args override .env — set before run_evaluation loads the app
    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider
    if args.model:
        os.environ["MODEL_NAME"] = args.model
    if args.judge_provider:
        os.environ["JUDGE_PROVIDER"] = args.judge_provider
    if args.judge_model:
        os.environ["JUDGE_MODEL"] = args.judge_model

    if not os.getenv("LANGSMITH_API_KEY"):
        raise ValueError("LANGSMITH_API_KEY not found. Please set it in your .env file.")

    run_evaluation(temperature=args.temperature, example_index=args.example)
