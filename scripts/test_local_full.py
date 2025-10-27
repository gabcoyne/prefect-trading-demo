"""
Full local test script that runs child flow directly without deployments.
This is for testing the logic before deploying to K8s.
"""

import pandas as pd
from flows.analyze_contract_flow import analyze_contract


def test_multiple_contracts():
    """Test the analyze_contract flow with multiple contracts locally."""

    print("=" * 80)
    print("Trading Partition Demo - Full Local Test")
    print("=" * 80)
    print()
    print("Testing multiple contracts locally (no deployments needed)")
    print()

    # Test with first 3 contracts
    contracts = ["AAPL", "MSFT", "GOOGL"]

    print(f"Testing with {len(contracts)} contracts: {', '.join(contracts)}")
    print(f"Will process all available time slices from parquet")
    print()

    results = []

    for contract in contracts:
        print(f"\n{'='*80}")
        print(f"Processing {contract}...")
        print(f"{'='*80}\n")

        try:
            # Run the flow
            result = analyze_contract(
                contract=contract,
                parquet_path="s3://se-demo-raw-data-files/spx_holdings_hourly.parquet",
                output_dir="output/test_results",
            )

            results.append(
                {"contract": contract, "output_file": result, "status": "success"}
            )

            # Read and display summary
            output_df = pd.read_parquet(result)
            print(f"\n✓ {contract} completed:")
            print(f"  - Total trades: {output_df['total_trades'].iloc[0]}")
            print(f"  - Good trades: {output_df['good_trades'].iloc[0]}")
            print(f"  - Bad trades: {output_df['bad_trades'].iloc[0]}")
            print(f"  - Success rate: {output_df['success_rate'].iloc[0]:.2f}%")
            print(f"  - Output: {result}")

        except Exception as e:
            print(f"\n✗ {contract} failed: {e}")
            results.append(
                {
                    "contract": contract,
                    "output_file": None,
                    "status": "failed",
                    "error": str(e),
                }
            )

    print(f"\n\n{'='*80}")
    print("Summary")
    print(f"{'='*80}")
    print(f"\nProcessed {len(contracts)} contracts:")

    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]

    print(f"  ✓ Successful: {len(successful)}")
    print(f"  ✗ Failed: {len(failed)}")

    if successful:
        print(f"\nSuccessful contracts:")
        for r in successful:
            print(f"  - {r['contract']}: {r['output_file']}")

    if failed:
        print(f"\nFailed contracts:")
        for r in failed:
            print(f"  - {r['contract']}: {r['error']}")

    print(f"\n{'='*80}")
    print("\n✓ Local test complete!")
    print("\nNext steps:")
    print("  1. Deploy to Prefect Cloud: uv run prefect deploy --all")
    print("  2. Run orchestrator: uv run python run_demo.py")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    test_multiple_contracts()
