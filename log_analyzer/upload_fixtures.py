"""
upload_fixtures.py
------------------
One-time script to upload log fixture files to a dedicated LangSmith dataset.
Fixtures are retrieved at eval time by name via _get_fixture() in evaluate.py.

Run once:
    python upload_fixtures.py

Re-run with --force to overwrite existing fixtures:
    python upload_fixtures.py --force
"""

import argparse
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client

load_dotenv(override=True, dotenv_path=".env")

FIXTURE_DATASET = "log-analyzer-fixtures"
FIXTURES_DIR = Path(__file__).parent / "data/fixtures"

FIXTURE_FILES = {
    "example_0_errors":    "example_0_errors.log",
    "example_1_http":      "example_1_http.log",
    "example_2_auth":      "example_2_auth.log",
    "example_3_critical":  "example_3_critical.log",
    "example_4_traceback": "example_4_traceback.log",
    "example_5_traffic":   "example_5_traffic.log",
}


def upload_fixtures(force: bool = False) -> None:
    client = Client()

    # Create dataset if it doesn't exist
    try:
        client.read_dataset(dataset_name=FIXTURE_DATASET)
        print(f"📁 Using existing dataset: {FIXTURE_DATASET}")
    except Exception:
        client.create_dataset(
            dataset_name=FIXTURE_DATASET,
            description="Raw log fixtures for log-analyzer eval examples. One fixture per example, keyed by name.",
        )
        print(f"📁 Created dataset: {FIXTURE_DATASET}")

    # Check existing fixtures
    existing = {
        ex.inputs.get("name"): ex
        for ex in client.list_examples(dataset_name=FIXTURE_DATASET)
    }

    if existing and not force:
        print(f"⏭️  {len(existing)} fixtures already uploaded. Use --force to overwrite.")
        for name in existing:
            print(f"   • {name}")
        return

    if existing and force:
        print(f"🗑️  Deleting {len(existing)} existing fixtures...")
        for ex in existing.values():
            client.delete_example(ex.id)

    # Upload all fixtures
    inputs, outputs = [], []
    for name, filename in FIXTURE_FILES.items():
        path = FIXTURES_DIR / filename
        if not path.exists():
            print(f"⚠️  Missing fixture file: {path} — skipping")
            continue
        content = path.read_text()
        inputs.append({"name": name, "content": content})
        outputs.append({"source_file": filename})
        print(f"   • {name}  ({len(content.splitlines())} lines)")

    client.create_examples(
        inputs=inputs,
        outputs=outputs,
        dataset_name=FIXTURE_DATASET,
    )
    print(f"\n✅ Uploaded {len(inputs)} fixtures to '{FIXTURE_DATASET}'")
    print(f"   View at: https://smith.langchain.com/datasets")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload log fixtures to LangSmith.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete and re-upload all fixtures even if they already exist.",
    )
    args = parser.parse_args()
    upload_fixtures(force=args.force)
