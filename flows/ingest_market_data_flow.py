"""
Data ingestion flow to fetch live market data from Yahoo Finance.
Fetches stock prices, VIX (volatility index), and S&P 500 index data.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional
from prefect import flow, task
from prefect.artifacts import create_markdown_artifact
import yfinance as yf


@task(log_prints=True, retries=2, retry_delay_seconds=5)
def fetch_stock_data(
    symbols: List[str], start_date: str, end_date: str, interval: str = "1h"
):
    """
    Fetch stock price data from Yahoo Finance.

    Args:
        symbols: List of stock ticker symbols
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        interval: Data interval (1h for hourly, 1d for daily)

    Returns:
        DataFrame with stock prices indexed by timestamp
    """
    print(f"Fetching data for {len(symbols)} symbols from {start_date} to {end_date}")

    # Fetch data for all symbols
    data_frames = []
    successful = []
    failed = []

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval=interval)

            if not df.empty:
                # Use close prices
                df_close = df[["Close"]].rename(columns={"Close": symbol})
                data_frames.append(df_close)
                successful.append(symbol)
            else:
                failed.append(symbol)
                print(f"  ⚠️  No data for {symbol}")
        except Exception as e:
            failed.append(symbol)
            print(f"  ⚠️  Failed to fetch {symbol}: {e}")

    if not data_frames:
        raise ValueError("No data fetched for any symbols")

    # Combine all dataframes
    combined_df = pd.concat(data_frames, axis=1)
    combined_df.index.name = "timestamp"

    print(f"✓ Successfully fetched {len(successful)} symbols")
    print(f"  Records per symbol: {len(combined_df)}")
    if failed:
        print(
            f"  ⚠️  Failed: {', '.join(failed[:10])}{' ...' if len(failed) > 10 else ''}"
        )

    return combined_df


@task(log_prints=True, retries=2, retry_delay_seconds=5)
def fetch_vix_data(start_date: str, end_date: str, interval: str = "1h"):
    """
    Fetch VIX (volatility index) data from Yahoo Finance.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        interval: Data interval

    Returns:
        DataFrame with VIX values
    """
    print(f"Fetching VIX data from {start_date} to {end_date}")

    try:
        ticker = yf.Ticker("^VIX")
        df = ticker.history(start=start_date, end=end_date, interval=interval)

        if df.empty:
            raise ValueError("No VIX data available")

        vix_df = df[["Close"]].rename(columns={"Close": "VIX"})
        vix_df.index.name = "timestamp"

        print(f"✓ Fetched {len(vix_df)} VIX records")
        print(f"  VIX range: {vix_df['VIX'].min():.2f} to {vix_df['VIX'].max():.2f}")

        return vix_df
    except Exception as e:
        print(f"⚠️  Failed to fetch VIX: {e}")
        raise


@task(log_prints=True, retries=2, retry_delay_seconds=5)
def fetch_spx_data(start_date: str, end_date: str, interval: str = "1h"):
    """
    Fetch S&P 500 index data from Yahoo Finance.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        interval: Data interval

    Returns:
        DataFrame with SPX values
    """
    print(f"Fetching S&P 500 data from {start_date} to {end_date}")

    try:
        ticker = yf.Ticker("^GSPC")
        df = ticker.history(start=start_date, end=end_date, interval=interval)

        if df.empty:
            raise ValueError("No S&P 500 data available")

        spx_df = df[["Close"]].rename(columns={"Close": "SPX"})
        spx_df.index.name = "timestamp"

        print(f"✓ Fetched {len(spx_df)} S&P 500 records")
        print(f"  SPX range: {spx_df['SPX'].min():.2f} to {spx_df['SPX'].max():.2f}")

        return spx_df
    except Exception as e:
        print(f"⚠️  Failed to fetch S&P 500: {e}")
        raise


@task(log_prints=True)
def save_to_parquet(df: pd.DataFrame, output_path: str):
    """
    Save DataFrame to parquet file.

    Args:
        df: DataFrame to save
        output_path: Output file path (local or S3)

    Returns:
        Output path
    """
    print(f"Saving to {output_path}...")
    df.to_parquet(output_path, engine="pyarrow", compression="snappy")
    print(f"✓ Saved {len(df)} records")
    return output_path


@flow(
    name="ingest-market-data",
    flow_run_name="ingest-{symbols_count}-symbols",
    persist_result=True,
    log_prints=True,
)
def ingest_market_data(
    symbols: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    interval: str = "1h",
    output_stocks_path: str = "s3://se-demo-raw-data-files/spx_holdings_hourly.parquet",
    output_vix_path: str = "s3://se-demo-raw-data-files/vix_hourly.parquet",
    output_spx_path: str = "s3://se-demo-raw-data-files/spx_hourly.parquet",
):
    """
    Ingest live market data from Yahoo Finance.

    Fetches stock prices, VIX, and S&P 500 index data and saves to parquet files.

    Args:
        symbols: List of stock symbols (default: top 10 S&P 500 stocks)
        start_date: Start date in YYYY-MM-DD format (default: 5 days ago)
        end_date: End date in YYYY-MM-DD format (default: today)
        interval: Data interval (1h for hourly, 1d for daily)
        output_stocks_path: Output path for stock data
        output_vix_path: Output path for VIX data
        output_spx_path: Output path for S&P 500 data

    Returns:
        Dictionary with output paths
    """
    # Set defaults
    if symbols is None:
        # Default to top 10 S&P 500 stocks by market cap
        symbols = [
            "AAPL",
            "MSFT",
            "GOOGL",
            "AMZN",
            "NVDA",
            "META",
            "TSLA",
            "BRK-B",
            "V",
            "UNH",
        ]

    if start_date is None:
        start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    # Create summary artifact
    create_markdown_artifact(
        key="ingestion-summary",
        markdown=f"""# Market Data Ingestion

**Date Range**: {start_date} to {end_date}  
**Interval**: {interval}  
**Symbols**: {len(symbols)}

## Symbols
{', '.join(symbols)}

## Output Files
- Stocks: `{output_stocks_path}`
- VIX: `{output_vix_path}`
- S&P 500: `{output_spx_path}`
        """,
        description="Data ingestion summary",
    )

    # Fetch all data in parallel
    stocks_df = fetch_stock_data(symbols, start_date, end_date, interval)
    vix_df = fetch_vix_data(start_date, end_date, interval)
    spx_df = fetch_spx_data(start_date, end_date, interval)

    # Save all data
    stocks_path = save_to_parquet(stocks_df, output_stocks_path)
    vix_path = save_to_parquet(vix_df, output_vix_path)
    spx_path = save_to_parquet(spx_df, output_spx_path)

    return {
        "stocks_path": stocks_path,
        "vix_path": vix_path,
        "spx_path": spx_path,
        "symbols_count": len(symbols),
        "records_count": len(stocks_df),
    }


if __name__ == "__main__":
    # Test with local paths
    result = ingest_market_data(
        symbols=["AAPL", "MSFT", "GOOGL"],
        start_date="2024-10-15",
        end_date="2024-10-18",
        output_stocks_path="output/test_stocks.parquet",
        output_vix_path="output/test_vix.parquet",
        output_spx_path="output/test_spx.parquet",
    )
    print(f"\n✓ Ingestion complete: {result}")
