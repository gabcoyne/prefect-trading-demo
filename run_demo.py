"""
Demo runner for the trading partition demo.
This requires deployments to be registered first.

For local testing without deployments, use scripts/test_local.py instead.
"""

import os
from flows.orchestrator_flow import trading_orchestrator

# Reduce logging noise
os.environ.setdefault("PREFECT_LOGGING_LEVEL", "WARNING")


def main():
    """Run the trading orchestrator (requires deployments)."""
    print("=" * 80)
    print("Trading Partition Demo - Orchestrator Run")
    print("=" * 80)
    print()
    print("⚠️  IMPORTANT: This script requires deployments to be registered and")
    print("              data uploaded to S3.")
    print()
    print("If you haven't deployed yet, run:")
    print("  1. uv run python scripts/create_ecr_repo.py")
    print("  2. uv run python scripts/upload_data_to_s3.py")
    print("  3. aws ecr get-login-password --region us-east-2 | \\")
    print("       docker login --username AWS --password-stdin \\")
    print("       455346737763.dkr.ecr.us-east-2.amazonaws.com")
    print("  4. uv run prefect deploy --all")
    print()
    print("If you made code changes, redeploy:")
    print("  uv run prefect deploy --all")
    print()
    print("For local testing WITHOUT deployments:")
    print("  uv run python scripts/test_local.py")
    print()
    print("=" * 80)
    print()

    print()
    print("Running orchestrator...")
    print()

    # Run the orchestrator flow
    # Note: Use S3 paths since child flows run in K8s
    result = trading_orchestrator(
        parquet_path="s3://se-demo-raw-data-files/spx_holdings_hourly.parquet",
        num_contracts=10,
        output_dir="s3://se-demo-raw-data-files/trading-results",
        child_deployment_name="analyze-contract/analyze-contract",
    )

    print()
    print("=" * 80)
    print("✓ Orchestrator completed!")
    print(f"✓ Triggered {len(result)} child flow runs")
    print()
    print("Flow run details:")
    for run_info in result:
        print(f"  - {run_info['contract']}: {run_info['flow_run_name']}")
    print()
    print("Monitor in Prefect Cloud:")
    print("  - View flow runs")
    print("  - Filter by tags: contract:AAPL, time_slice:10, etc.")
    print("  - Check artifacts for trade summaries")
    print("=" * 80)


if __name__ == "__main__":
    main()
