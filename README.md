# Trading Data Pipeline Demo for Prefect

A production-ready demonstration of orchestrating parallel trading analysis workloads with market context enrichment, designed to showcase patterns common in quantitative trading firms.

## Why This Demo Matters for Trading Firms

**Real-world trading data teams face:**
- Processing hundreds of symbols in parallel at scale
- Incorporating market context (volatility, correlations, indices)
- Reprocessing specific symbols when models change
- Data quality validation before expensive compute
- Portfolio-level aggregation across individual analyses
- Fast iteration cycles for strategy development

**This demo shows how Prefect handles:**
- ✅ **Parallel symbol processing** across distributed K8s workers
- ✅ **Market context enrichment** (VIX volatility, S&P 500 beta)
- ✅ **Granular reprocessing** (single symbol or full portfolio)
- ✅ **Data validation gates** before analysis
- ✅ **Portfolio aggregation** with P&L, Sharpe ratio, win rates
- ✅ **Simple parameterization** for easy operation

## Architecture Overview

### 5-Deployment Pipeline

```
1. Data Ingestion (optional)
   └─> Fetch live data from Yahoo Finance
   
2. Data Validation (optional)
   └─> Quality checks, outlier detection
   
3. Main Orchestrator
   └─> Triggers 10 parallel symbol flows
   
4. Symbol Analysis × 10 (parallel)
   └─> Each processes all timestamps with market context
   
5. Portfolio Aggregation (standalone)
   └─> Cross-symbol analytics and metrics
```

### Execution Pattern

**Single Command**: `prefect deployment run orchestrator/orchestrator --param num_contracts=10`

**Result**: 10 parallel K8s jobs, each analyzing one symbol across 28,048 hourly data points with VIX-adjusted signals and beta calculation.

## Key Features for Trading Workflows

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

**Why it matters**: Realistic trading strategies must adapt to market conditions. This demo shows how to incorporate volatility regimes and market correlation into signal generation.

### 2. Flexible Reprocessing

**Full Portfolio**:
```bash
prefect deployment run orchestrator/orchestrator --param num_contracts=100
```

**Single Symbol** (after model updates):
```bash
prefect deployment run analyze-symbol/analyze-symbol --param contract="AAPL"
```

**Why it matters**: Trading firms constantly refine models. Being able to reprocess specific symbols without rerunning the entire portfolio saves time and compute costs.

### 3. Data Quality Gates

**Validation checks before expensive processing**:
- Missing value detection across symbols
- Price outlier identification (z-score > 3σ)
- Market data availability verification
- Fails fast on critical data issues

**Why it matters**: Running expensive analysis on bad data wastes resources. Validation gates catch issues early.

### 4. Portfolio-Level Analytics

After symbol-level analysis, aggregate to portfolio view:
- Total P&L across all positions
- Sharpe ratio calculation
- Win rate by symbol and time period
- Contract performance comparison

**Why it matters**: Individual symbol performance matters less than portfolio-level risk-adjusted returns.

### 5. Production Patterns

- **Parallel execution**: 10 K8s jobs running simultaneously
- **Result persistence**: S3 storage for all outputs
- **Retry logic**: Automatic retries on API failures
- **Comprehensive artifacts**: Performance summaries in Prefect UI
- **Simple parameters**: Just `num_contracts` or `contract`

## Quick Start

### Prerequisites
- Python 3.9+
- `uv` package manager
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

**Note**: Upload these to S3 before running flows (see step 3). All flows pull data from S3.

```bash
# Upload to S3
python scripts/upload_data_to_s3.py
```

### 2. Test Locally

```bash
# Install dependencies
uv sync

# Test single symbol flow
python flows/analyze_symbol_flow.py

# Verify output
ls -lh output/test_results/AAPL_analysis.parquet
```

### 3. Deploy to K8s

```bash
# Create ECR repository (first time only)
python scripts/create_ecr_repo.py

# Upload data to S3
python scripts/upload_data_to_s3.py

# Authenticate with ECR
aws ecr get-login-password --region us-east-2 | \
  docker login --username AWS --password-stdin \
  455346737763.dkr.ecr.us-east-2.amazonaws.com

# Deploy all 5 flows
prefect deploy --all
```

### 4. Run the Pipeline

```bash
# Process 10 symbols (default)
prefect deployment run orchestrator/orchestrator

# Process 5 symbols
prefect deployment run orchestrator/orchestrator --param num_contracts=5

# Reprocess single symbol
prefect deployment run analyze-symbol/analyze-symbol --param contract="MSFT"

# Aggregate portfolio (after orchestrator completes)
prefect deployment run aggregate-portfolio/aggregate-portfolio
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
- Load symbol prices for all timestamps
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
s3://se-demo-raw-data-files/trading-results/
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

## Use Cases for Trading Firms

### Backtesting Pipeline
Run historical strategy analysis across entire universe:
```bash
prefect deployment run orchestrator/orchestrator --param num_contracts=500
```

### Model Iteration
Rerun specific symbols after model updates:
```bash
prefect deployment run analyze-symbol/analyze-symbol --param contract="TSLA"
```

### Live Data Integration
Fetch fresh market data and process:
```bash
prefect deployment run ingest-market-data/ingest-market-data \
  --param symbols='["AAPL","MSFT","GOOGL"]' \
  --param start_date="2024-10-15" \
  --param end_date="2024-10-20"
```

### Portfolio Risk Analysis
After analysis, compute portfolio metrics:
```bash
prefect deployment run aggregate-portfolio/aggregate-portfolio
```

### Data Quality Validation
Standalone data quality checks:
```bash
prefect deployment run validate-data/validate-data
```

## Architecture Patterns for Trading Firms

### 1. Partition by Symbol
**Problem**: Need to analyze 500+ symbols
**Solution**: Orchestrator triggers one flow per symbol, runs in parallel on K8s
**Benefit**: Linear scaling with K8s worker count

### 2. Market Context as First-Class Data
**Problem**: Signals need market regime awareness
**Solution**: VIX and SPX joined at data load, used in signal generation
**Benefit**: Strategies adapt to volatility and market direction

### 3. Granular Reprocessing
**Problem**: Model changes require reprocessing specific symbols
**Solution**: Symbol flows deployable independently
**Benefit**: Reprocess changed symbols only, not entire universe

### 4. Validation Gates
**Problem**: Bad data causes wasted compute on invalid analysis
**Solution**: Validation flow runs first, fails fast on data issues
**Benefit**: Save money by catching bad data early

### 5. Portfolio Aggregation
**Problem**: Need portfolio-level metrics, not just symbol-level
**Solution**: Separate aggregation flow after symbol analysis completes
**Benefit**: Portfolio metrics (Sharpe, P&L) calculated across all symbols

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
│   ├── create_ecr_repo.py             # ECR setup
│   └── test_local*.py                 # Local testing
├── docs/
│   ├── ARCHITECTURE.md                # Detailed architecture
│   ├── ALGORITHM.md                   # Trading strategy explanation
│   └── TROUBLESHOOTING.md             # Common issues
├── prefect.yaml                        # 5 deployment definitions
├── pyproject.toml                      # Dependencies (includes yfinance)
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

## Why Prefect for Trading Workflows

### vs Airflow
- **Dynamic DAGs**: Prefect handles variable symbol counts naturally
- **Retry Logic**: Per-task retries without manual orchestration
- **Result Passing**: Native result serialization between tasks
- **Deployment Simplicity**: `prefect deploy --all` vs complex DAG management

### vs Custom Scripts
- **Observability**: Built-in UI, logs, artifacts
- **Fault Tolerance**: Automatic retries, failure handling
- **Scheduling**: Cron, interval, event-driven triggers
- **Distributed Execution**: K8s integration out of the box

### vs Notebooks
- **Production Ready**: Deployable, scheduled, monitored
- **Parallel Execution**: Not sequential like notebooks
- **Version Control**: Python code, not JSON notebooks
- **Collaboration**: Teams can iterate on flows independently

## Advanced Features

### Artifacts
Every flow creates rich artifacts in Prefect UI:
- **Orchestrator**: Pipeline summary with contract list
- **Symbol**: Per-symbol metrics (trades, win rate, beta, VIX)
- **Validation**: Data quality tables with outliers
- **Aggregation**: Portfolio performance tables

### Tags
Filter and monitor by:
- `contract:AAPL` - All runs for AAPL
- `symbol` - All symbol analysis flows
- `orchestrator` - Main orchestration runs

### Concurrency
Built-in concurrency limits prevent resource exhaustion:
```python
@task(tags=["contract:AAPL"])  # Prefect can limit concurrent AAPL tasks
```

## Production Considerations

### Cost Optimization
- Process only changed symbols when models update
- Use spot instances for K8s workers
- Store compressed parquet results
- Aggregate results expire old data

### Monitoring
- Prefect UI shows all flow runs, task status
- Artifacts provide performance metrics
- Failed flows trigger alerts
- Retry logic handles transient failures

### Data Versioning
- S3 versioning enabled on input bucket
- Results include timestamp of analysis
- Can reprocess historical data with new models

## Documentation

- [Architecture Details](docs/ARCHITECTURE.md) - System design
- [Algorithm Explanation](docs/ALGORITHM.md) - Trading strategy
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md) - Common issues
- [Simplified Summary](SIMPLIFIED_SUMMARY.md) - Architecture changes

## Real-World Applications

This pattern generalizes to:
- **Risk Analysis**: Calculate VaR/CVaR per position, aggregate to portfolio
- **Market Making**: Update quotes for 1000s of instruments in parallel
- **Alpha Research**: Backtest strategies across universes
- **Position Sizing**: Compute allocations based on portfolio constraints
- **Compliance Checks**: Validate trades against limits in parallel

## License

MIT License - Demo purposes only

## Disclaimer

⚠️ **Not Financial Advice**: This is a technical demonstration. The trading algorithm is intentionally simple and should not be used for real trading. Always consult qualified financial advisors for investment decisions.
