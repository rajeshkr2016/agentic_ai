import os
from pathlib import Path
from langsmith import Client
from dotenv import load_dotenv

load_dotenv()

def upload_logs_to_langsmith(dataset_name: str, log_dir: str):
    client = Client()
    
    # 1. Create the dataset (or get existing)
    if not client.has_dataset(dataset_name=dataset_name):
        dataset = client.create_dataset(
            dataset_name=dataset_name, 
            description="Dataset of server logs for error analysis benchmarking."
        )
    else:
        dataset = client.read_dataset(dataset_name=dataset_name)

    # 2. Prepare examples from local files
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

    # 3. Bulk upload examples
    if examples:
        client.create_examples(
            dataset_id=dataset.id,
            inputs=[e["inputs"] for e in examples],
            outputs=[e["outputs"] for e in examples]
        )
        print(f"Successfully uploaded {len(examples)} logs to dataset: {dataset_name}")

if __name__ == "__main__":
    LOG_DIRECTORY = os.getenv("LOG_DIRECTORY", "./logs")
    upload_logs_to_langsmith("Production_Log_Benchmarks", LOG_DIRECTORY)
