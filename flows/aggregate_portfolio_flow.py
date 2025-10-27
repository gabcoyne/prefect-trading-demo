"""
Portfolio aggregation flow to summarize results across all contracts.
Calculates portfolio-level metrics, P&L, Sharpe ratio, and win rates.
"""

import pandas as pd
import numpy as np
from typing import List, Optional
from pathlib import Path
from prefect import flow, task
from prefect.artifacts import create_markdown_artifact, create_table_artifact


@task(log_prints=True)
def load_all_results(output_dir: str, contracts: Optional[List[str]] = None):
    """
    Load all contract analysis results from output directory.

    Args:
        output_dir: Directory containing analysis results
        contracts: Optional list of contracts to load (None = all)

    Returns:
        Combined DataFrame with all results
    """
    print(f"Loading results from {output_dir}")

    all_results = []

    if output_dir.startswith("s3://"):
        # For S3, we'll need to list and read files
        # For simplicity in this demo, assume results are in contract subdirectories
        import s3fs

        fs = s3fs.S3FileSystem()

        if contracts is None:
            # List all subdirectories (contracts)
            try:
                contract_dirs = fs.ls(output_dir)
                contracts = [Path(d).name for d in contract_dirs]
            except Exception as e:
                print(f"⚠️  Failed to list S3 directories: {e}")
                contracts = []

        for contract in contracts:
            try:
                contract_dir = f"{output_dir}/{contract}"
                files = fs.glob(f"{contract_dir}/*.parquet")

                for file_path in files:
                    df = pd.read_parquet(f"s3://{file_path}")
                    all_results.append(df)
            except Exception as e:
                print(f"⚠️  Failed to load results for {contract}: {e}")
    else:
        # Local filesystem
        output_path = Path(output_dir)

        if not output_path.exists():
            raise ValueError(f"Output directory not found: {output_dir}")

        # Find all parquet files in contract subdirectories
        parquet_files = list(output_path.glob("*/*.parquet"))

        print(f"Found {len(parquet_files)} result files")

        for file_path in parquet_files:
            try:
                df = pd.read_parquet(file_path)
                all_results.append(df)
            except Exception as e:
                print(f"⚠️  Failed to load {file_path}: {e}")

    if not all_results:
        raise ValueError("No results found to aggregate")

    # Combine all results
    combined_df = pd.concat(all_results, ignore_index=True)

    # Ensure timestamp is datetime
    combined_df["timestamp"] = pd.to_datetime(combined_df["timestamp"])

    # Sort by contract and timestamp
    combined_df = combined_df.sort_values(["contract", "timestamp"])

    print(
        f"✓ Loaded {len(combined_df)} records for {combined_df['contract'].nunique()} contracts"
    )

    return combined_df


@task(log_prints=True)
def evaluate_trade_quality(df: pd.DataFrame):
    """
    Evaluate trade quality based on subsequent price movements.

    Args:
        df: DataFrame with trade signals

    Returns:
        DataFrame with trade quality added
    """
    print("Evaluating trade quality...")

    df = df.copy()
    df = df.sort_values(["contract", "timestamp"])

    # Calculate next price change for each contract
    df["next_price_change_pct"] = df.groupby("contract")["price_change_pct"].shift(-1)

    # Evaluate trade quality
    df["trade_quality"] = "neutral"

    # Good trade: buy before price increase, or sell before price decrease
    df.loc[
        ((df["signal"] == "buy") & (df["next_price_change_pct"] > 0))
        | ((df["signal"] == "sell") & (df["next_price_change_pct"] < 0)),
        "trade_quality",
    ] = "good"

    # Bad trade: buy before price decrease, or sell before price increase
    df.loc[
        ((df["signal"] == "buy") & (df["next_price_change_pct"] < 0))
        | ((df["signal"] == "sell") & (df["next_price_change_pct"] > 0)),
        "trade_quality",
    ] = "bad"

    good_trades = (df["trade_quality"] == "good").sum()
    bad_trades = (df["trade_quality"] == "bad").sum()

    print(f"✓ Evaluated trades: {good_trades} good, {bad_trades} bad")

    return df


@task(log_prints=True)
def calculate_portfolio_metrics(df: pd.DataFrame):
    """
    Calculate portfolio-level metrics.

    Args:
        df: DataFrame with all trades and quality

    Returns:
        Dictionary with portfolio metrics
    """
    print("Calculating portfolio metrics...")

    # Overall statistics
    total_records = len(df)
    total_contracts = df["contract"].nunique()

    # Trade statistics
    total_trades = len(df[df["signal"] != "hold"])
    good_trades = len(df[df["trade_quality"] == "good"])
    bad_trades = len(df[df["trade_quality"] == "bad"])
    win_rate = (good_trades / total_trades * 100) if total_trades > 0 else 0

    # Portfolio P&L (simplified)
    # Assume equal allocation to each trade
    df["trade_pnl"] = 0.0
    df.loc[df["signal"] == "buy", "trade_pnl"] = df["next_price_change_pct"]
    df.loc[df["signal"] == "sell", "trade_pnl"] = -df["next_price_change_pct"]

    total_pnl = df["trade_pnl"].sum()
    avg_pnl_per_trade = df[df["signal"] != "hold"]["trade_pnl"].mean()

    # Calculate Sharpe ratio (simplified)
    trade_returns = df[df["signal"] != "hold"]["trade_pnl"].dropna()
    if len(trade_returns) > 1:
        sharpe_ratio = (
            trade_returns.mean() / trade_returns.std() if trade_returns.std() > 0 else 0
        )
    else:
        sharpe_ratio = 0

    # Average beta across portfolio
    avg_beta = df["beta"].mean()

    # Average VIX
    avg_vix = df["vix"].mean()

    # Time series metrics
    timestamps = df["timestamp"].nunique()
    date_range = f"{df['timestamp'].min():%m/%d/%Y} to {df['timestamp'].max():%m/%d/%Y}"

    metrics = {
        "total_records": total_records,
        "total_contracts": total_contracts,
        "total_timestamps": timestamps,
        "date_range": date_range,
        "total_trades": total_trades,
        "good_trades": good_trades,
        "bad_trades": bad_trades,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "avg_pnl_per_trade": avg_pnl_per_trade,
        "sharpe_ratio": sharpe_ratio,
        "avg_beta": avg_beta,
        "avg_vix": avg_vix,
    }

    print(f"✓ Portfolio metrics calculated")
    print(f"  Win Rate: {win_rate:.2f}%")
    print(f"  Total P&L: {total_pnl:.2f}%")
    print(f"  Sharpe Ratio: {sharpe_ratio:.3f}")

    return metrics


@task(log_prints=True)
def create_portfolio_artifacts(df: pd.DataFrame, metrics: dict):
    """
    Create comprehensive portfolio artifacts.

    Args:
        df: Full DataFrame with all results
        metrics: Portfolio metrics dictionary
    """
    print("Creating portfolio artifacts...")

    # Main summary artifact
    create_markdown_artifact(
        key="portfolio-summary",
        markdown=f"""# Portfolio Analysis Summary

## Overview
- **Date Range**: {metrics['date_range']}
- **Contracts Analyzed**: {metrics['total_contracts']}
- **Time Periods**: {metrics['total_timestamps']}
- **Total Records**: {metrics['total_records']:,}

## Trading Performance
- **Total Trades**: {metrics['total_trades']:,}
- **Win Rate**: {metrics['win_rate']:.2f}%
- **Good Trades**: {metrics['good_trades']:,}
- **Bad Trades**: {metrics['bad_trades']:,}

## Financial Metrics
- **Total P&L**: {metrics['total_pnl']:.2f}%
- **Avg P&L per Trade**: {metrics['avg_pnl_per_trade']:.2f}%
- **Sharpe Ratio**: {metrics['sharpe_ratio']:.3f}

## Market Context
- **Average Beta**: {metrics['avg_beta']:.2f}
- **Average VIX**: {metrics['avg_vix']:.2f}
        """,
        description="Portfolio-level performance summary",
    )

    # Top performers table
    contract_performance = (
        df.groupby("contract")
        .agg(
            {
                "trade_quality": lambda x: (x == "good").sum(),
                "signal": lambda x: (x != "hold").sum(),
                "beta": "mean",
                "price_change_pct": "mean",
            }
        )
        .reset_index()
    )

    contract_performance.columns = [
        "Contract",
        "Good Trades",
        "Total Trades",
        "Avg Beta",
        "Avg Return",
    ]
    contract_performance["Win Rate"] = (
        contract_performance["Good Trades"] / contract_performance["Total Trades"] * 100
    ).round(2)
    contract_performance = contract_performance.sort_values("Win Rate", ascending=False)

    create_table_artifact(
        key="contract-performance",
        table=contract_performance.head(20).to_dict("records"),
        description="Top 20 contracts by win rate",
    )

    # Time series performance
    time_performance = (
        df.groupby("timestamp")
        .agg(
            {
                "trade_quality": lambda x: (x == "good").sum(),
                "signal": lambda x: (x != "hold").sum(),
                "vix": "mean",
                "price_change_pct": "mean",
            }
        )
        .reset_index()
    )

    time_performance.columns = [
        "Timestamp",
        "Good Trades",
        "Total Trades",
        "VIX",
        "Avg Return",
    ]
    time_performance["Win Rate"] = (
        time_performance["Good Trades"] / time_performance["Total Trades"] * 100
    ).round(2)

    # Show first and last 10 time periods
    display_records = pd.concat(
        [time_performance.head(10), time_performance.tail(10)]
    ).to_dict("records")

    create_table_artifact(
        key="time-series-performance",
        table=display_records,
        description="Performance over time (first and last 10 periods)",
    )

    print("✓ Artifacts created")


@flow(
    name="aggregate-portfolio",
    flow_run_name="portfolio-aggregation",
    persist_result=True,
    log_prints=True,
)
def aggregate_portfolio(
    output_dir: str = "s3://se-demo-raw-data-files/trading-results",
    contracts: Optional[List[str]] = None,
):
    """
    Aggregate and analyze portfolio-level results.

    This flow runs after the orchestrator completes to provide
    comprehensive portfolio analytics across all contracts and time periods.

    Calculates:
    - Portfolio-level P&L
    - Win rates and trade quality
    - Sharpe ratio
    - Contract-level performance
    - Time series analysis

    Args:
        output_dir: Directory containing analysis results
        contracts: Optional list of contracts to aggregate (None = all)

    Returns:
        Portfolio metrics dictionary
    """
    # Load all results
    df = load_all_results(output_dir, contracts)

    # Evaluate trade quality (needs full time series)
    df = evaluate_trade_quality(df)

    # Calculate portfolio metrics
    metrics = calculate_portfolio_metrics(df)

    # Create artifacts
    create_portfolio_artifacts(df, metrics)

    return metrics


if __name__ == "__main__":
    # Test with local paths
    result = aggregate_portfolio(
        output_dir="output/test_results",
    )
    print(f"\nPortfolio metrics: {result}")
