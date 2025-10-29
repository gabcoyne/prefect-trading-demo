# Trading Data Pipeline Demo for Prefect

A production-ready demonstration of orchestrating parallel trading analysis workloads with market context enrichment using Prefect on Kubernetes.

## What This Demo Shows

**Parallel symbol processing** across distributed K8s workers with market context enrichment (VIX volatility, S&P 500 beta calculation).

Single command triggers 10 parallel K8s jobs, each analyzing one symbol across 28,048 hourly data points with VIX-adjusted signals.

## Architecture

### 2-Layer Deployment Structure

```
Orchestrator Flow
  └─> Triggers N Symbol Flows in parallel
  
Symbol Flow × N (parallel K8s jobs)
  └─> Each processes all timestamps for one contract
```

**Execution**:
```bash
prefect deployment run orchestrator/orchestrator --param num_contracts=10
```

**Result**: 10 parallel K8s jobs running simultaneously, each analyzing ~28K timestamps.

## Key Features

### 1. Market Context Enrichment

Every analysis includes real market context:

**VIX-Adjusted Signals**:
```python
# Higher volatility → more conservative thresholds
buy_threshold = 0.5 * (VIX / 15.0)
sell_threshold = -0.5 * (VIX / 15.0)
```

**Beta Calculation**:
```python
# Stock correlation with S&P 500 at each timestamp
beta = stock_change_pct / spx_change_pct
```

### 2. Flexible Reprocessing

**Full Portfolio**:
```bash
prefect deployment run orchestrator/orchestrator --param num_contracts=100
```

**Single Symbol**:
```bash
prefect deployment run analyze-symbol/analyze-symbol --param contract="AAPL"
```

### 3. Production Patterns

- **Parallel execution**: N K8s jobs running simultaneously
- **S3 storage**: Prefect S3 blocks for data and results management
- **Result persistence**: Parquet files with full analysis results
- **Simple parameters**: Just `num_contracts` or `contract`

## Quick Start

### Prerequisites
- Python 3.9+ with `uv` package manager
- AWS credentials configured
- Prefect Cloud account
- K8s work pool named `demo_eks`

### 1. Generate Sample Data

```bash
cd input
python generate_hourly_data.py
cd ..
```

This creates local parquet files:
- `spx_holdings_hourly.parquet` - 419 stocks, 28,048 timestamps
- `vix_hourly.parquet` - Volatility index
- `spx_hourly.parquet` - S&P 500 index

### 2. Create S3 Blocks

Create Prefect S3 blocks for data storage:
```bash
python scripts/create_s3_blocks.py
```

This creates two S3 blocks:
- `trading-demo-input` - For raw data files (spx_holdings, vix, spx)
- `trading-demo-results` - For analysis output files

Upload data to S3 (all flows pull data from S3):
```bash
python scripts/upload_data_to_s3.py
```

### 3. Test Locally

```bash
# Install dependencies
uv sync

# Test single symbol flow
python flows/analyze_symbol_flow.py

# Verify output
ls -lh output/test_results/AAPL_analysis.parquet
```

### 4. Deploy to K8s

```bash
# Create ECR repository (first time only)
python scripts/create_ecr_repo.py

# Authenticate with ECR
aws ecr get-login-password --region us-east-2 | \
  docker login --username AWS --password-stdin \
  455346737763.dkr.ecr.us-east-2.amazonaws.com

# Deploy both flows (orchestrator + symbol)
prefect deploy --all
```

### 5. Run the Pipeline

```bash
# Process 10 symbols (default)
prefect deployment run orchestrator/orchestrator

# Process 5 symbols
prefect deployment run orchestrator/orchestrator --param num_contracts=5

# Reprocess single symbol
prefect deployment run analyze-symbol/analyze-symbol --param contract="MSFT"
```

## Data Pipeline Details

### Input Data

**Stock Holdings**: `spx_holdings_hourly.parquet`
- 419 S&P 500 constituents
- 28,048 hourly timestamps (2000-2013)
- 8 hours per trading day (9:30 AM - 4:00 PM EST)

**Market Indices**:
- `vix_hourly.parquet` - CBOE Volatility Index
- `spx_hourly.parquet` - S&P 500 Index

### Analysis Flow (Per Symbol)

Each symbol flow executes a 3-task pipeline:

**Task 1: Load with Market Context**
- Load symbol prices for all timestamps from S3
- Join VIX volatility data
- Join S&P 500 index data

**Task 2: Analyze with Market Context**
- Calculate price changes and momentum
- Compute beta (correlation with S&P 500)
- Generate VIX-adjusted buy/sell signals
- Evaluate trade quality vs subsequent prices

**Task 3: Save and Summarize**
- Save enriched results to parquet
- Create performance artifact (trades, win rate, beta)

### Output Structure

```
s3://se-demo-raw-data-files/trading-results/  (K8s)
output/test_results/                           (local)
├── AAPL_analysis.parquet    # 28K rows with signals, beta, VIX
├── MSFT_analysis.parquet
└── ... (one per symbol)
```

Each file includes:
- `timestamp`, `contract`, `price`, `price_change_pct`
- `VIX`, `SPX`, `spx_change_pct`
- `beta` - correlation with market
- `signal` - buy/sell/hold
- `buy_threshold`, `sell_threshold` - VIX-adjusted
- `trade_quality` - good/bad/neutral

## Trading Algorithm

**Momentum Strategy with Volatility Adjustment**:

1. **Signal Generation**:
   - Buy when price increase > threshold
   - Sell when price decrease < -threshold
   - Thresholds adjust with VIX (higher VIX = wider thresholds)

2. **Quality Evaluation**:
   - Good trade: Buy before increase, sell before decrease
   - Bad trade: Buy before decrease, sell before increase
   - Neutral: Hold or end of series

3. **Market Context**:
   - Beta shows if stock moves with/against market
   - VIX adjustment prevents overtrading in volatile markets

⚠️ **Disclaimer**: Demo algorithm only, not for real trading.

## Project Structure

```
trading-partition-demo/
├── flows/
│   ├── orchestrator_flow.py           # Main coordinator
│   └── analyze_symbol_flow.py         # Per-symbol analysis with market context
├── input/
│   └── generate_hourly_data.py        # Sample data generation (includes VIX/SPX)
├── scripts/
│   ├── upload_data_to_s3.py           # S3 data upload
│   └── create_ecr_repo.py             # ECR setup
├── prefect.yaml                        # 2 deployment definitions
├── pyproject.toml                      # Dependencies
└── Dockerfile                          # K8s container image
```

## Performance Characteristics

**With 10 symbols (default)**:
- Parallel K8s jobs: 10
- Data points analyzed: 280,480 (10 × 28,048)
- Runtime: 2-5 minutes
- Output files: 10 parquet files (~2-3 MB each)

**Scaling**:
- 100 symbols: 10-15 minutes (K8s auto-scaling)
- 500 symbols: 30-45 minutes
- Each symbol is completely independent

## Common Issues

### FileNotFoundError for parquet files
**Solution**: Make sure data is uploaded to S3:
```bash
python scripts/upload_data_to_s3.py
```

### Docker authentication expired
**Solution**: Re-authenticate with ECR (tokens expire after 12 hours):
```bash
aws ecr get-login-password --region us-east-2 | \
  docker login --username AWS --password-stdin \
  455346737763.dkr.ecr.us-east-2.amazonaws.com
```

### Flows stuck in Pending
**Solution**: Check that your K8s work pool has active workers:
```bash
prefect work-pool ls
```

## License

MIT License - Demo purposes only

## Disclaimer

⚠️ **Not Financial Advice**: This is a technical demonstration. The trading algorithm is intentionally simple and should not be used for real trading.
