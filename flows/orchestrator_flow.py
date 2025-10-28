"""
Parent orchestrator flow that coordinates the entire trading pipeline.
Supports optional data ingestion, validation, and triggers symbol analysis flows on K8s.
"""

import pandas as pd
from typing import Optional, List
from prefect import flow, task
from prefect.deployments import run_deployment
from prefect.artifacts import create_markdown_artifact


@task(log_prints=False)
def load_and_partition_data(parquet_path: str, num_contracts: Optional[int] = None):
    """
    Load parquet data and extract contract list.

    Args:
        parquet_path: Path to the SPX holdings parquet file
        num_contracts: Optional limit on number of contracts to process (for demo)

    Returns:
        Tuple of (contracts list, total timestamps count, parquet_path)
    """
    # Load the parquet file
    df = pd.read_parquet(parquet_path)

    # Get all contracts (columns except 'SPX' which is the index itself)
    all_contracts = [col for col in df.columns if col != "SPX"]

    # Limit contracts if specified (for demo purposes)
    if num_contracts:
        contracts = all_contracts[:num_contracts]
    else:
        contracts = all_contracts

    # Get timestamp count for reporting
    total_timestamps = len(df.index.unique())

    return contracts, total_timestamps, parquet_path


@task(log_prints=False)
def trigger_symbol_analysis(contract: str, symbol_index: int):
    """
    Trigger a symbol analysis flow for a specific contract.

    Args:
        contract: Stock contract to analyze
        symbol_index: Index of this symbol in the batch (for demo failure simulation)

    Returns:
        Flow run details
    """
    # Trigger the symbol deployment with contract and index parameters
    flow_run = run_deployment(
        name="analyze-symbol/analyze-symbol",
        parameters={
            "contract": contract,
            "symbol_index": symbol_index,
        },
        timeout=0,  # Don't wait for completion
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
)
def trading_orchestrator(
    num_contracts: int = 10,
):
    """
    Orchestrate the trading pipeline across parallel symbol flows.

    This orchestrator:
    1. Loads the SPX holdings data
    2. Partitions by contract
    3. Triggers parallel symbol flows for analysis

    Architecture: Orchestrator → N Parallel Symbol Flows (each processes all timestamps)

    Each symbol flow:
    - Loads contract data with VIX and SPX
    - Calculates beta (correlation with S&P 500)
    - Generates VIX-adjusted trading signals
    - Evaluates trade quality

    Args:
        num_contracts: Number of contracts to process (default 10 for demo)

    Returns:
        List of triggered symbol flow runs
    """
    # Configuration (hardcoded for simplicity)
    parquet_path = "s3://se-demo-raw-data-files/spx_holdings_hourly.parquet"

    # Load and partition data
    contracts, total_timestamps, _ = load_and_partition_data(
        parquet_path, num_contracts
    )

    # Create summary artifact
    create_markdown_artifact(
        key="orchestrator-summary",
        markdown=f"""# Trading Pipeline Orchestration

## Architecture
**Orchestrator** → **{len(contracts)} Symbol Flows** (each processes {total_timestamps} timestamps internally)

## Processing Scope
- **Contracts**: {len(contracts)}
- **Timestamps per Contract**: {total_timestamps}
- **Total Analysis Points**: {len(contracts) * total_timestamps}
- **Parallel Symbol Flows**: {len(contracts)}

## Data Sources
- **Stock Data**: `{parquet_path}`
- **VIX & SPX Data**: Configured in symbol flows
- **Output Directory**: Configured in symbol flows

## Contracts
{', '.join(contracts[:20])}{'...' if len(contracts) > 20 else ''}

## Market Context Features
- **Beta Calculation**: Stock correlation with S&P 500
- **VIX-Adjusted Signals**: Higher volatility → more conservative thresholds
- **Trade Quality**: Evaluated based on subsequent price movements
        """,
        description="Trading pipeline orchestration summary",
    )

    # Trigger symbol flows for each contract (in parallel)
    # Each symbol flow processes all timestamps internally
    flow_runs = []
    for idx, contract in enumerate(contracts):
        flow_run = trigger_symbol_analysis(contract=contract, symbol_index=idx)
        flow_runs.append(flow_run)

    print(f"\n{'='*60}")
    print(f"✓ Triggered {len(flow_runs)} symbol flows")
    print(f"✓ Each analyzes {total_timestamps} timestamps with market context")
    print(
        f"✓ Total analysis: {len(flow_runs)} × {total_timestamps} = {len(flow_runs) * total_timestamps} data points"
    )
    print(f"{'='*60}")

    return flow_runs


if __name__ == "__main__":
    trading_orchestrator()
