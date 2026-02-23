import os
from pathlib import Path
from langsmith import Client
from dotenv import load_dotenv

load_dotenv()

# Import evaluation module
try:
    from evaluate import run_evaluation
except ImportError:
    run_evaluation = None

def upload_logs_to_langsmith(logs_dataset_name: str, log_dir: str, project_name: str = None):
    client = Client()
    
    # Set default project name
    if project_name is None:
        project_name = os.getenv("LANGSMITH_PROJECT", "log-analyzer")
    
    print(f"📦 Using project: {project_name}")
    
    # 1. Create/get the project (application)
    project = None
    try:
        # Try to get existing project
        project = client.read_project(project_name=project_name)
        print(f"✅ Found existing project: {project_name}")
    except Exception:
        # Create new project if it doesn't exist
        try:
            project = client.create_project(
                project_name=project_name,
                metadata={"description": "Log analyzer application"}
            )
            print(f"✅ Created new project: {project_name}")
        except Exception as e:
            print(f"⚠️  Project operation failed: {e}")
            print(f"   Continuing with project: {project_name}")
    
    # Extract project URL
    project_url = None
    if project:
        project_url = getattr(project, "url", None)
        if not project_url:
            # Fallback: construct URL from project name
            project_url = f"https://smith.langchain.com/projects/{project_name}"
    
    # 2. Create the dataset (or get existing)
    if not client.has_dataset(dataset_name=logs_dataset_name):
        dataset = client.create_dataset(
            dataset_name=logs_dataset_name, 
            description="Dataset of server logs for error analysis benchmarking."
        )
        print(f"✅ Created new dataset: {logs_dataset_name}")
    else:
        dataset = client.read_dataset(dataset_name=logs_dataset_name)
        print(f"✅ Found existing dataset: {logs_dataset_name}")

    # 3. Prepare examples from local files
    log_path = Path(log_dir)
    examples = []
    
    for log_file in log_path.glob("*.log"):
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()
            # We map 'input' to what the agent receives
            examples.append({
                "inputs": {"log_content": content, "filename": log_file.name},
                "outputs": {"expected_analysis": "Manually add known root cause here"} 
            })

    # 4. Bulk upload examples
    if examples:
        client.create_examples(
            dataset_id=dataset.id,
            inputs=[e["inputs"] for e in examples],
            outputs=[e["outputs"] for e in examples]
        )
        print(f"✅ Uploaded {len(examples)} logs to dataset: {logs_dataset_name}")
    else:
        print(f"⚠️  No log files found in {log_dir}")
    
    return project_url

if __name__ == "__main__":
    LOG_DIRECTORY = os.getenv("LOG_DIRECTORY", "./logs")
    PROJECT_NAME = os.getenv("LANGSMITH_PROJECT", "log-analyzer")
    
    print("=" * 60)
    print("🚀 Starting LangSmith Upload & Evaluation Pipeline")
    print("=" * 60)
    
    # Use consistent dataset name
    # dataset_name = f"{PROJECT_NAME}-dataset"

    logs_dataset_name = f"{PROJECT_NAME}-logs"
    
    # Step 1: Upload logs
    print("\n📤 Step 1: Uploading logs to LangSmith...")
    print("-" * 60)
    project_url = upload_logs_to_langsmith(logs_dataset_name, LOG_DIRECTORY, PROJECT_NAME)
    
    # Step 2: Run evaluation
    if run_evaluation:
        print("\n\n🧪 Step 2: Running evaluation experiment...")
        print("-" * 60)
        try:
            run_evaluation(project_name=PROJECT_NAME, project_url=project_url)
        except Exception as e:
            print(f"❌ Evaluation failed with error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n⚠️  Evaluation module not available. Skipping evaluation step.")
        print("   Make sure evaluate.py is in the same directory.")
    
    print("\n" + "=" * 60)
    print("✅ Pipeline completed!")
    print("=" * 60)
