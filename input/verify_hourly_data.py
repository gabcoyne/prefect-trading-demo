"""
Verify the generated hourly stock data.
"""

import pandas as pd


def verify_hourly_data(parquet_file: str):
    """Load and display sample of hourly data."""
    print(f"Reading {parquet_file}...\n")

    df = pd.read_parquet(parquet_file)

    print("=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"Total records: {len(df):,}")
    print(f"Number of stocks: {len(df.columns)}")
    print(f"Date range: {df.index.min()} to {df.index.max()}")
    print(f"Index timezone: {df.index.tz}")

    print("\n" + "=" * 80)
    print("SAMPLE DATA - First Day (2000-01-27)")
    print("=" * 80)
    first_day = df[df.index.date == df.index.min().date()]
    print(first_day[["A", "AAPL", "MSFT", "SPX"]].round(2))

    print("\n" + "=" * 80)
    print("SAMPLE DATA - Random Day (2005-06-15)")
    print("=" * 80)
    try:
        sample_day = df[df.index.date == pd.Timestamp("2005-06-15").date()]
        if len(sample_day) > 0:
            print(sample_day[["A", "AAPL", "MSFT", "SPX"]].round(2))
        else:
            print("Date not in dataset")
    except:
        print("Date not in dataset")

    print("\n" + "=" * 80)
    print("DATA QUALITY CHECKS")
    print("=" * 80)
    print(f"Missing values: {df.isna().sum().sum()}")
    print(
        f"Records per day (should be 8): {len(df) / (len(df.index.normalize().unique())):.1f}"
    )


if __name__ == "__main__":
    verify_hourly_data("spx_holdings_hourly.parquet")
