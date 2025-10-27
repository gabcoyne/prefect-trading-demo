# Simplified Trading Pipeline Architecture

## Overview

A realistic, production-ready trading demo with **5 deployments** showing good fan-out without excessive complexity.

## Architecture

```
5-Deployment Structure (Fast & Practical)

1. Ingestion Flow (optional)
   └─> Fetches live data from Yahoo Finance
   
2. Validation Flow (optional)
   └─> Data quality checks
   
3. Orchestrator
   └─> Triggers 10 parallel symbol flows
   
4. Symbol Flows × 10 (parallel)
   └─> Each processes 24 timestamps internally
   
5. Aggregation Flow (standalone)
   └─> Portfolio analytics
```

**Total Flows**: 1 orchestrator + 10 symbols = **11 concurrent flows** (not 240!)

## Flow Descriptions

### 1. Data Ingestion (`ingest-market-data`)
- Fetches stock prices, VIX, SPX from Yahoo Finance
- Hourly data for configurable date range
- Retry logic for API failures
- Can run standalone or triggered by orchestrator

### 2. Data Validation (`validate-data`)
- Missing value detection
- Price outlier analysis (z-score)
- Market data availability check
- Returns PASS/WARN/FAIL status

### 3. Main Orchestrator (`orchestrator`)
- Optional ingestion trigger
- Optional validation trigger
- Loads and partitions contract data
- **Triggers 10 symbol flows in parallel**

### 4. Symbol Flow (`analyze-symbol`) - The Core
Each symbol flow:
- Loads contract data + VIX + SPX
- **Calculates beta** (stock vs market correlation)
- **VIX-adjusted signals** (higher VIX = more conservative)
- Processes **all 24 timestamps internally**
- Evaluates trade quality
- Saves results with summary artifact

**Key Features**:
- Beta calculation per timestamp
- Dynamic buy/sell thresholds based on VIX
- Market context enrichment
- 3-task pattern: load → analyze → save

### 5. Portfolio Aggregation (`aggregate-portfolio`)
- Loads all symbol results
- Portfolio-level P&L calculation
- Sharpe ratio
- Win rate analysis
- Time series performance
- Contract comparison tables

## Why This Is Better

### Before (Too Complex)
- 240 time partition flows (10 contracts × 24 timestamps)
- Each flow analyzes 1 data point
- Takes forever to spawn and coordinate
- Hard to debug with so many flows

### After (Simplified)
- 10 symbol flows (one per contract)
- Each flow analyzes 24 data points internally
- Fast to run (10 parallel flows, not 240)
- Still shows good fan-out pattern
- Easier to debug and monitor

## Deployment Matrix

| Deployment            | Type             | Triggered By              | Waits?      | Purpose               |
| --------------------- | ---------------- | ------------------------- | ----------- | --------------------- |
| `ingest-market-data`  | Standalone/Child | Orchestrator or manual    | Yes (5 min) | Fetch live data       |
| `validate-data`       | Standalone/Child | Orchestrator or manual    | Yes (2 min) | Quality gates         |
| `orchestrator`        | Parent           | Manual or schedule        | No          | Coordinate pipeline   |
| `analyze-symbol`      | Child            | Orchestrator              | No          | Per-contract analysis |
| `aggregate-portfolio` | Standalone       | Manual (after completion) | N/A         | Final analytics       |

## Usage

### Quick Demo (with existing data)
```bash
# Generate sample data
cd input && python generate_hourly_data.py && cd ..

# Deploy
prefect deploy --all

# Run with validation
prefect deployment run orchestrator/orchestrator
```

### With Live Data
```bash
prefect deployment run orchestrator/orchestrator \
  --param run_ingestion=true \
  --param ingestion_symbols='["AAPL","MSFT","GOOGL","AMZN","TSLA"]' \
  --param num_contracts=5
```

### Reprocess One Symbol
```bash
prefect deployment run analyze-symbol/analyze-symbol \
  --param contract="AAPL"
```

### Portfolio Analytics
```bash
# After orchestrator completes
prefect deployment run aggregate-portfolio/aggregate-portfolio
```

## Local Testing

```bash
# Test symbol flow directly
python flows/analyze_symbol_flow.py

# Test with local files
python flows/test_local_flows.py
```

## Performance

With default settings (10 contracts):
- **Concurrent flows**: 11 (1 orchestrator + 10 symbols)
- **Analysis points**: 10 contracts × 24 timestamps = 240 data points
- **Runtime**: ~2-5 minutes (depending on K8s scaling)
- **Much faster than**: 240 separate flow runs!

## Market Context Features

### Beta Calculation
```python
beta = stock_change_pct / market_change_pct
```
- Shows correlation with S&P 500
- Clipped to [-3, 3] to avoid outliers
- Calculated per timestamp

### VIX-Adjusted Thresholds
```python
buy_threshold = 0.5 * (VIX / 15.0)
sell_threshold = -0.5 * (VIX / 15.0)
```
- Higher VIX → wider thresholds → fewer trades
- Lower VIX → tighter thresholds → more trades
- Dynamic risk management

### Trade Quality
- **Good**: Buy before increase, sell before decrease
- **Bad**: Buy before decrease, sell before increase
- **Neutral**: Hold or end of series

## Data Flow

```
Input Files:
  ├─ spx_holdings_hourly.parquet (stock prices)
  ├─ vix_hourly.parquet (volatility)
  └─ spx_hourly.parquet (market index)

↓ [Validation]

↓ [Orchestrator]

↓ [10 Symbol Flows in Parallel]

Output Files:
  ├─ AAPL_analysis.parquet
  ├─ MSFT_analysis.parquet
  └─ ... (one per symbol)

↓ [Aggregation]

Portfolio Metrics:
  ├─ Total P&L
  ├─ Sharpe Ratio
  ├─ Win Rate
  └─ Time Series Performance
```

## Artifacts

Each layer creates rich artifacts:
1. **Ingestion**: Data source summary
2. **Validation**: Quality report with tables
3. **Orchestrator**: Pipeline overview
4. **Symbol**: Per-contract summary with beta/VIX
5. **Aggregation**: Portfolio metrics and comparisons

## Next Steps

1. Generate data: `cd input && python generate_hourly_data.py`
2. Deploy: `prefect deploy --all`
3. Run: `prefect deployment run orchestrator/orchestrator`
4. View in Prefect UI: See the fan-out graph!
5. Aggregate: `prefect deployment run aggregate-portfolio/aggregate-portfolio`

