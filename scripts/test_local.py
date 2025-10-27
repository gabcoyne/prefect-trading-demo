"""
Local test script to validate flow logic without deployments.
Tests the child flow with sample data.
"""

import pandas as pd
from flows.analyze_contract_flow import analyze_contract


def test_analyze_contract_flow():
    """Test the analyze_contract flow with a single contract."""

    print("=" * 80)
    print("Testing analyze_contract flow locally")
    print("=" * 80)
    print()

    # Test with AAPL
    contract = "AAPL"

    print(f"Testing with contract: {contract}")
    print(f"Will process all available time slices from parquet")
    print()
    print("Running flow...")
    print()

    # Run the flow
    result = analyze_contract(
        contract=contract,
        parquet_path="spx_holdings_hourly.parquet",
        output_dir="output/test_results",
    )

    print()
    print("=" * 80)
    print(f"Flow completed!")
    print(f"Output file: {result}")
    print("=" * 80)
    print()

    # Read and display the output
    output_df = pd.read_parquet(result)
    print("Output data sample:")
    print(output_df.head(10))
    print()
    print(f"Total rows: {len(output_df)}")
    print(f"Good trades: {output_df['good_trades'].iloc[0]}")
    print(f"Bad trades: {output_df['bad_trades'].iloc[0]}")
    print(f"Success rate: {output_df['success_rate'].iloc[0]:.2f}%")


if __name__ == "__main__":
    test_analyze_contract_flow()
