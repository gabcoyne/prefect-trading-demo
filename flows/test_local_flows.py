"""
Local testing script that calls flows directly without deployments.
Use this to test the multi-layer architecture locally before deploying.
"""

from analyze_time_partition_flow import analyze_time_partition
from analyze_symbol_flow import analyze_symbol
from orchestrator_flow import trading_orchestrator


def test_time_partition_locally():
    """Test a single time partition flow."""
    print("Testing time partition flow...")

    result = analyze_time_partition(
        contract="AAPL",
        timestamp="2024-01-02 09:30:00-05:00",
        parquet_path="s3://se-demo-raw-data-files/spx_holdings_hourly.parquet",
        vix_path="s3://se-demo-raw-data-files/vix_hourly.parquet",
        spx_path="s3://se-demo-raw-data-files/spx_hourly.parquet",
        output_dir="output/test_results",
    )

    print(f"✓ Time partition result: {result}")
    return result


def test_symbol_flow_locally():
    """
    Test symbol flow by calling time partition flows directly.
    This bypasses the deployment trigger mechanism.
    """
    print("Testing symbol flow (direct calls, not via deployment)...")

    import pandas as pd

    contract = "AAPL"
    parquet_path = "s3://se-demo-raw-data-files/spx_holdings_hourly.parquet"
    vix_path = "s3://se-demo-raw-data-files/vix_hourly.parquet"
    spx_path = "s3://se-demo-raw-data-files/spx_hourly.parquet"
    output_dir = "output/test_results"

    # Load timestamps
    df = pd.read_parquet(parquet_path)
    timestamps = [ts.isoformat() for ts in df.index.tolist()[:3]]  # Test with first 3

    print(f"Processing {contract} with {len(timestamps)} timestamps...")

    # Call time partition flows directly (not via deployment)
    results = []
    for timestamp in timestamps:
        result = analyze_time_partition(
            contract=contract,
            timestamp=timestamp,
            parquet_path=parquet_path,
            vix_path=vix_path,
            spx_path=spx_path,
            output_dir=output_dir,
        )
        results.append(result)
        print(f"  ✓ Processed {timestamp}")

    print(f"✓ Symbol flow complete: {len(results)} partitions processed")
    return results


if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("LOCAL TESTING MODE")
    print("=" * 60)
    print("\nNote: This tests flows directly without deployments.")
    print("For full deployment testing, run: prefect deploy --all\n")

    if len(sys.argv) > 1:
        test = sys.argv[1]
        if test == "partition":
            test_time_partition_locally()
        elif test == "symbol":
            test_symbol_flow_locally()
        else:
            print(f"Unknown test: {test}")
            print("Usage: python test_local_flows.py [partition|symbol]")
    else:
        print("Running time partition test...\n")
        test_time_partition_locally()

        print("\n" + "=" * 60)
        print("\nTo test symbol flow (with 3 timestamps):")
        print("  python test_local_flows.py symbol")
