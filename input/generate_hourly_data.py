"""
Generate hourly stock price data from daily data.

Converts daily closing prices to hourly prices during trading hours (9:30 AM - 4:00 PM EST)
using linear interpolation between consecutive days.
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
import pytz


def generate_hourly_data(input_csv: str, output_parquet: str):
    """
    Generate hourly stock data from daily CSV and save as parquet.

    Args:
        input_csv: Path to input CSV file with daily prices
        output_parquet: Path to output parquet file
    """
    # Read the CSV file
    print(f"Reading {input_csv}...")
    df = pd.read_csv(input_csv)

    # First column is unnamed and contains dates
    date_col = df.columns[0]
    df = df.rename(columns={date_col: "date"})

    # Parse dates
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    print(f"Loaded {len(df)} days of data for {len(df.columns) - 1} stocks")

    # Define trading hours in EST
    est = pytz.timezone("US/Eastern")
    trading_hours = [
        time(9, 30),  # Market open
        time(10, 30),
        time(11, 30),
        time(12, 30),
        time(13, 30),
        time(14, 30),
        time(15, 30),
        time(16, 0),  # Market close
    ]

    # Create hourly data
    hourly_records = []
    stock_columns = [col for col in df.columns if col != "date"]

    print("Generating hourly data with linear interpolation...")

    for i in range(len(df)):
        date = df.iloc[i]["date"]

        # Get current day's values
        current_values = df.iloc[i][stock_columns].values

        # Get next day's values for interpolation (if available)
        if i < len(df) - 1:
            next_values = df.iloc[i + 1][stock_columns].values
        else:
            # For the last day, just use current values
            next_values = current_values

        # Generate hourly timestamps and interpolated values
        for hour_idx, trading_time in enumerate(trading_hours):
            # Create timezone-aware timestamp
            timestamp = est.localize(datetime.combine(date.date(), trading_time))

            # Calculate interpolation factor (0 at market open, 1 at next day's market open)
            # We assume the daily price is the closing price at 4:00 PM
            if i < len(df) - 1:
                # Interpolate between today's close and tomorrow's close
                # Within the trading day, progress from today's close towards tomorrow's close
                interp_factor = hour_idx / len(trading_hours)
                interpolated_values = (
                    current_values + (next_values - current_values) * interp_factor
                )
            else:
                # Last day: just use current values
                interpolated_values = current_values

            # Create record
            record = {"timestamp": timestamp}
            for col_idx, col_name in enumerate(stock_columns):
                record[col_name] = interpolated_values[col_idx]

            hourly_records.append(record)

    # Create DataFrame from hourly records
    hourly_df = pd.DataFrame(hourly_records)
    hourly_df = hourly_df.set_index("timestamp")

    print(f"Generated {len(hourly_df)} hourly records")

    # Save to parquet
    print(f"Saving to {output_parquet}...")
    hourly_df.to_parquet(output_parquet, engine="pyarrow", compression="snappy")

    print("✓ Done!")
    print(f"\nOutput statistics:")
    print(f"  - Records: {len(hourly_df)}")
    print(f"  - Stocks: {len(stock_columns)}")
    print(f"  - Date range: {hourly_df.index.min()} to {hourly_df.index.max()}")
    print(f"  - File size: {output_parquet}")


def generate_market_indices(input_csv: str, output_vix: str, output_spx: str):
    """
    Generate hourly VIX and SPX index data from daily CSV.

    Args:
        input_csv: Path to input CSV file with daily prices (must contain SPX column)
        output_vix: Path to output VIX parquet file
        output_spx: Path to output SPX parquet file
    """
    # Read the CSV file
    print(f"\nGenerating market indices from {input_csv}...")
    df = pd.read_csv(input_csv)

    # First column is unnamed and contains dates
    date_col = df.columns[0]
    df = df.rename(columns={date_col: "date"})
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # Define trading hours in EST
    est = pytz.timezone("US/Eastern")
    trading_hours = [
        time(9, 30),
        time(10, 30),
        time(11, 30),
        time(12, 30),
        time(13, 30),
        time(14, 30),
        time(15, 30),
        time(16, 0),
    ]

    # Generate SPX hourly data (extract from input CSV)
    print("Generating SPX hourly data...")
    spx_records = []

    for i in range(len(df)):
        date = df.iloc[i]["date"]
        current_spx = df.iloc[i]["SPX"]
        next_spx = df.iloc[i + 1]["SPX"] if i < len(df) - 1 else current_spx

        for hour_idx, trading_time in enumerate(trading_hours):
            timestamp = est.localize(datetime.combine(date.date(), trading_time))
            interp_factor = hour_idx / len(trading_hours)
            interpolated_spx = current_spx + (next_spx - current_spx) * interp_factor
            spx_records.append({"timestamp": timestamp, "SPX": interpolated_spx})

    spx_df = pd.DataFrame(spx_records)
    spx_df = spx_df.set_index("timestamp")
    spx_df.to_parquet(output_spx, engine="pyarrow", compression="snappy")
    print(f"✓ Saved SPX data to {output_spx} ({len(spx_df)} records)")

    # Generate simulated VIX data (volatility index)
    # VIX typically ranges from 10-40, with mean around 15-20
    print("Generating simulated VIX hourly data...")
    np.random.seed(42)  # For reproducibility

    vix_records = []
    base_vix = 18.0  # Base volatility level

    for i in range(len(df)):
        date = df.iloc[i]["date"]

        # Calculate daily volatility based on SPX movements
        if i > 0:
            spx_change_pct = (
                abs((df.iloc[i]["SPX"] - df.iloc[i - 1]["SPX"]) / df.iloc[i - 1]["SPX"])
                * 100
            )
            # Higher SPX changes correlate with higher VIX
            daily_vix = base_vix + spx_change_pct * 5 + np.random.normal(0, 2)
        else:
            daily_vix = base_vix + np.random.normal(0, 2)

        # Ensure VIX stays in realistic range (10-50)
        daily_vix = max(10, min(50, daily_vix))

        # Generate hourly values with some intraday variation
        for hour_idx, trading_time in enumerate(trading_hours):
            timestamp = est.localize(datetime.combine(date.date(), trading_time))
            # Add intraday noise
            hourly_vix = daily_vix + np.random.normal(0, 1.5)
            hourly_vix = max(10, min(50, hourly_vix))
            vix_records.append({"timestamp": timestamp, "VIX": hourly_vix})

    vix_df = pd.DataFrame(vix_records)
    vix_df = vix_df.set_index("timestamp")
    vix_df.to_parquet(output_vix, engine="pyarrow", compression="snappy")
    print(f"✓ Saved VIX data to {output_vix} ({len(vix_df)} records)")
    print(f"  VIX range: {vix_df['VIX'].min():.2f} to {vix_df['VIX'].max():.2f}")


if __name__ == "__main__":
    input_file = "spx_holdings_and_spx_closeprice.csv"
    output_file = "spx_holdings_hourly.parquet"
    output_vix_file = "vix_hourly.parquet"
    output_spx_file = "spx_hourly.parquet"

    # Generate stock holdings data
    generate_hourly_data(input_file, output_file)

    # Generate market indices
    generate_market_indices(input_file, output_vix_file, output_spx_file)
