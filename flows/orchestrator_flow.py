"""Orchestrator flow that triggers parallel symbol analysis flows."""

import pandas as pd
from typing import Optional
from prefect import flow, task
from prefect.deployments import run_deployment
from prefect.artifacts import create_markdown_artifact
from prefect_aws import S3Bucket


@task(log_prints=False)
async def load_and_partition_data(num_contracts: Optional[int] = None):
    """Load parquet data and extract contract list."""
    s3_block = await S3Bucket.load("trading-demo-input")
    s3_path = f"s3://{s3_block.bucket_name}/spx_holdings_hourly.parquet"
    df = pd.read_parquet(s3_path)

    all_contracts = [col for col in df.columns if col != "SPX"]
    contracts = all_contracts[:num_contracts] if num_contracts else all_contracts
    total_timestamps = len(df.index.unique())

    return contracts, total_timestamps, s3_path


@task(log_prints=False)
def trigger_symbol_analysis(contract: str, symbol_index: int):
    """Trigger a symbol analysis flow for a specific contract."""
    flow_run = run_deployment(
        name="analyze-symbol/analyze-symbol",
        parameters={"contract": contract, "symbol_index": symbol_index},
        timeout=0,
    )

    return {
        "contract": contract,
        "flow_run_id": flow_run.id,
        "flow_run_name": flow_run.name,
    }


@flow(
    name="trading-orchestrator",
    flow_run_name="orchestrator-{num_contracts}-contracts",
    persist_result=True,
    log_prints=True,
    result_storage="s3-bucket/trading-demo-results",
)
async def trading_orchestrator(num_contracts: int = 10):
    """Orchestrate the trading pipeline across parallel symbol flows."""
    contracts, total_timestamps, parquet_path = await load_and_partition_data(num_contracts)

    await create_markdown_artifact(
        key="orchestrator-summary",
        markdown=f"""# Trading Pipeline Orchestration

**Orchestrator** → **{len(contracts)} Symbol Flows** (each processes {total_timestamps} timestamps)

- **Contracts**: {len(contracts)}
- **Total Analysis Points**: {len(contracts) * total_timestamps:,}
- **Data**: `{parquet_path}`
- **Contracts**: {', '.join(contracts[:20])}{'...' if len(contracts) > 20 else ''}
        """,
        description="Trading pipeline orchestration summary",
    )

    flow_runs = []
    for idx, contract in enumerate(contracts):
        flow_run = trigger_symbol_analysis(contract=contract, symbol_index=idx)
        flow_runs.append(flow_run)

    print(f"\n{'='*60}")
    print(f"✓ Triggered {len(flow_runs)} symbol flows")
    print(f"✓ Each analyzes {total_timestamps} timestamps with market context")
    print(f"✓ Total analysis: {len(flow_runs) * total_timestamps:,} data points")
    print(f"{'='*60}")

    return flow_runs


if __name__ == "__main__":
    import asyncio
    asyncio.run(trading_orchestrator())
