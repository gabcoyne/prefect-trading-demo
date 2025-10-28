"""
Symbol-level flow for analyzing a single contract across all timestamps.
Processes all time slices with market context (VIX, SPX, beta calculation).
"""

import pandas as pd
from prefect import flow, task
from prefect.artifacts import create_table_artifact
from prefect.runtime import flow_run as runtime_flow_run


@task(tags=["load"], log_prints=False)
def load_contract_with_market_data(
    contract: str, parquet_path: str, vix_path: str, spx_path: str
):
    """
    Load contract data with market context (VIX and SPX).

    Args:
        contract: Stock contract to analyze
        parquet_path: Path to stock holdings parquet
        vix_path: Path to VIX parquet
        spx_path: Path to SPX parquet

    Returns:
        DataFrame with contract prices, VIX, and SPX
    """
    # Load contract prices
    df = pd.read_parquet(parquet_path)
    df_contract = df[[contract]].copy()
    df_contract = df_contract.rename(columns={contract: "price"})
    df_contract["contract"] = contract

    # Load VIX
    vix_df = pd.read_parquet(vix_path)
    df_contract = df_contract.join(vix_df["VIX"], how="left")

    # Load SPX
    spx_df = pd.read_parquet(spx_path)
    df_contract = df_contract.join(spx_df["SPX"], how="left")

    # Reset index to make timestamp a column
    df_contract = df_contract.reset_index()
    df_contract = df_contract.rename(columns={"index": "timestamp"})

    return df_contract


@task(tags=["analyze"], log_prints=False)
def analyze_with_market_context(contract: str, df: pd.DataFrame):
    """
    Analyze trades with VIX-adjusted signals and beta calculation.

    Args:
        contract: Stock contract
        df: DataFrame with price, VIX, SPX data

    Returns:
        DataFrame with analysis including beta and volatility-adjusted signals
    """
    df = df.copy()
    df = df.sort_values("timestamp")

    # Calculate price changes
    df["price_change"] = df["price"].diff()
    df["price_change_pct"] = df["price"].pct_change(fill_method=None) * 100

    # Calculate SPX changes for beta
    df["spx_change_pct"] = df["SPX"].pct_change(fill_method=None) * 100

    # Calculate beta (simplified - stock change / market change)
    df["beta"] = df["price_change_pct"] / df["spx_change_pct"]
    df["beta"] = df["beta"].fillna(1.0)  # Neutral beta when undefined
    df["beta"] = df["beta"].clip(-3, 3)  # Clip extreme values

    # Volatility-adjusted signal thresholds
    # Higher VIX = more conservative (higher thresholds)
    base_vix = 15.0
    df["vix_multiplier"] = df["VIX"] / base_vix
    df["buy_threshold"] = 0.5 * df["vix_multiplier"]
    df["sell_threshold"] = -0.5 * df["vix_multiplier"]

    # Generate trading signals
    df["signal"] = "hold"
    df.loc[df["price_change_pct"] > df["buy_threshold"], "signal"] = "buy"
    df.loc[df["price_change_pct"] < df["sell_threshold"], "signal"] = "sell"

    # Evaluate trade quality
    df["next_price_change_pct"] = df["price_change_pct"].shift(-1)
    df["trade_quality"] = "neutral"

    # Good trades
    df.loc[
        ((df["signal"] == "buy") & (df["next_price_change_pct"] > 0))
        | ((df["signal"] == "sell") & (df["next_price_change_pct"] < 0)),
        "trade_quality",
    ] = "good"

    # Bad trades
    df.loc[
        ((df["signal"] == "buy") & (df["next_price_change_pct"] < 0))
        | ((df["signal"] == "sell") & (df["next_price_change_pct"] > 0)),
        "trade_quality",
    ] = "bad"

    return df


@task(tags=["save"], log_prints=False)
def save_and_summarize(contract: str, df: pd.DataFrame, output_dir: str):
    """
    Save results and create summary artifact.

    Args:
        contract: Stock contract
        df: Analysis results
        output_dir: Output directory

    Returns:
        Output path and summary stats
    """
    # Calculate summary statistics
    total_trades = len(df[df["signal"] != "hold"])
    good_trades = len(df[df["trade_quality"] == "good"])
    bad_trades = len(df[df["trade_quality"] == "bad"])
    success_rate = (good_trades / total_trades * 100) if total_trades > 0 else 0
    avg_beta = df["beta"].mean()
    avg_vix = df["VIX"].mean()

    # Save to parquet
    output_path = f"{output_dir}/{contract}_analysis.parquet"

    if output_dir.startswith("s3://"):
        df.to_parquet(output_path, engine="pyarrow", compression="snappy", index=False)
    else:
        import os

        os.makedirs(output_dir, exist_ok=True)
        df.to_parquet(output_path, engine="pyarrow", compression="snappy", index=False)

    # Create artifact
    create_table_artifact(
        key=f"{contract.lower()}-analysis-summary",
        table={
            "Contract": [contract],
            "Total Trades": [total_trades],
            "Good Trades": [good_trades],
            "Bad Trades": [bad_trades],
            "Win Rate": [f"{success_rate:.2f}%"],
            "Avg Beta": [f"{avg_beta:.2f}"],
            "Avg VIX": [f"{avg_vix:.2f}"],
        },
        description=f"Analysis summary for {contract} with market context",
    )

    return {
        "output_path": output_path,
        "total_trades": total_trades,
        "success_rate": success_rate,
        "avg_beta": avg_beta,
    }


@flow(
    name="analyze-symbol",
    flow_run_name="analyze-{contract}",
    persist_result=True,
    log_prints=False,
)
def analyze_symbol(
    contract: str,
    symbol_index: int = 0,
):
    """
    Analyze a single contract across all timestamps with market context.

    This flow:
    1. Loads contract data with VIX and SPX
    2. Calculates beta (correlation with S&P 500)
    3. Generates volatility-adjusted trading signals
    4. Evaluates trade quality
    5. Saves results with summary

    Args:
        contract: Stock contract to analyze
        symbol_index: Index of this symbol in the batch (for demo purposes)

    Returns:
        Summary statistics dictionary
    """
    # Configuration - check if running locally or in K8s
    import os
    
    # Demo: Simulate failure on the 8th symbol (index 7) to showcase error handling
    if symbol_index == 7:
        flow_run_id = runtime_flow_run.id
        flow_run_name = runtime_flow_run.name
        print(f"🔴 DEMO FAILURE: Simulating failure for symbol index {symbol_index} ({contract})")
        print(f"   Flow Run: {flow_run_name} (ID: {flow_run_id})")
        print(f"   This demonstrates Prefect's failure handling and retry capabilities")
        raise RuntimeError(
            f"Demo failure: Symbol index {symbol_index} ({contract}) failed intentionally. "
            f"This showcases Prefect's error handling. Configure retries to automatically recover."
        )

    # Detect environment: if /app exists, we're in K8s container
    is_k8s = os.path.exists("/app") and os.getcwd() == "/app"

    # Always pull input data from S3
    parquet_path = "s3://se-demo-raw-data-files/spx_holdings_hourly.parquet"
    vix_path = "s3://se-demo-raw-data-files/vix_hourly.parquet"
    spx_path = "s3://se-demo-raw-data-files/spx_hourly.parquet"
    
    # Output directory depends on environment
    if is_k8s:
        output_dir = "s3://se-demo-raw-data-files/trading-results"
    else:
        output_dir = "output/test_results"

    # Create contract-specific tags
    flow_tags = [f"contract:{contract}"]

    # Task A: Load data with market context
    df = load_contract_with_market_data.with_options(tags=flow_tags)(
        contract, parquet_path, vix_path, spx_path
    )

    # Task B: Analyze with VIX/SPX/beta
    df_analyzed = analyze_with_market_context.with_options(tags=flow_tags)(contract, df)

    # Task C: Save and summarize
    result = save_and_summarize.with_options(tags=flow_tags)(
        contract, df_analyzed, output_dir
    )

    return result


if __name__ == "__main__":
    analyze_symbol(contract="AAPL")
