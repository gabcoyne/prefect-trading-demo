# Multi-Layer Trading Pipeline Architecture

## Overview

This demo showcases a comprehensive, realistic multi-layer trading pipeline built with Prefect. The architecture demonstrates maximum fan-out visibility, data quality validation, market context enrichment, and portfolio-level analytics.

## Architecture Layers

### 6-Layer Deployment Structure

```
1. Data Ingestion Flow (ingest-market-data)
   └─> Fetches live data from Yahoo Finance API
   
2. Data Validation Flow (validate-data)
   └─> Quality checks before processing
   
3. Main Orchestrator Flow (orchestrator)
   └─> Coordinates entire pipeline
   
4. Symbol Flows (analyze-symbol) [10 parallel instances]
   └─> One per contract/stock
   
5. Time Partition Flows (analyze-time-partition) [240 parallel instances]
   └─> One per contract+timestamp combination
   
6. Portfolio Aggregation Flow (aggregate-portfolio)
   └─> Final analytics across all results
```

## Flow Hierarchy

### Level 1: Data Ingestion
**File**: `flows/ingest_market_data_flow.py`

Fetches live market data from Yahoo Finance:
- Stock prices for configurable symbols
- VIX (volatility index) data
- S&P 500 index data
- Saves to S3 or local parquet files

**Key Features**:
- Retry logic for API failures
- Parallel data fetching
- Automatic date range defaults
- Comprehensive ingestion artifacts

### Level 2: Data Validation
**File**: `flows/validate_data_flow.py`

Quality checks before expensive processing:
- Missing value detection across contracts
- Price outlier identification (z-score analysis)
- Market data availability verification
- Returns PASS/WARN/FAIL status

**Key Features**:
- Statistical outlier detection (>3σ)
- Data completeness checks
- Detailed validation artifacts with tables
- Fails fast on critical issues

### Level 3: Main Orchestrator
**File**: `flows/orchestrator_flow.py`

Top-level coordinator for the entire pipeline:
1. Optionally triggers data ingestion
2. Optionally triggers data validation
3. Loads and partitions contract data
4. Triggers symbol flows in parallel
5. Creates comprehensive orchestration artifact

**Configuration Options**:
- `run_ingestion`: Enable/disable live data fetch
- `run_validation`: Enable/disable quality checks
- `num_contracts`: Limit contracts for demo (default: 10)

### Level 4: Symbol Flow (Middle Layer)
**File**: `flows/analyze_symbol_flow.py`

Orchestrates time partition analysis for a single contract:
1. Extracts all timestamps for the contract
2. Triggers time partition flow for each timestamp
3. Creates symbol-level summary artifact

**Fan-out**: Each symbol flow spawns N time partition flows (N = number of timestamps)

### Level 5: Time Partition Flow (Leaf Level)
**File**: `flows/analyze_time_partition_flow.py`

Analyzes a single contract at a single timestamp:
1. **Load**: Fetches contract price + VIX + SPX for that timestamp
2. **Analyze**: 
   - Calculates beta (correlation with S&P 500)
   - Generates volatility-adjusted trading signals
   - Higher VIX → more conservative thresholds
3. **Save**: Stores result organized by contract subdirectory

**Market Context Enrichment**:
- Beta calculation vs S&P 500
- VIX-based signal adjustment
- Dynamic buy/sell thresholds

### Level 6: Portfolio Aggregation
**File**: `flows/aggregate_portfolio_flow.py`

Standalone flow for final analytics:
1. Loads all time partition results
2. Evaluates trade quality (needs full time series)
3. Calculates portfolio metrics:
   - Total P&L
   - Win rate (good trades / total trades)
   - Sharpe ratio
   - Average beta
4. Creates comprehensive artifacts:
   - Portfolio summary
   - Contract performance table
   - Time series performance

## Data Flow

```
Yahoo Finance API
    ↓
[Ingestion Flow] → Stock Data, VIX, SPX (S3/local parquet)
    ↓
[Validation Flow] → Quality Report (PASS/WARN/FAIL)
    ↓
[Orchestrator] → Triggers 10 Symbol Flows
    ↓
[Symbol Flow × 10] → Each triggers 24 Time Partition Flows
    ↓
[Time Partition × 240] → Individual results (contract/timestamp.parquet)
    ↓
[Aggregation Flow] → Portfolio metrics and analytics
```

## Key Enhancements

### 1. Live Data Integration
- Yahoo Finance API integration via `yfinance`
- Hourly data for realistic intraday analysis
- Automatic VIX and S&P 500 fetching

### 2. Data Quality Validation
- Pre-processing quality gates
- Statistical outlier detection
- Missing data identification
- Fails fast on critical issues

### 3. Market Context
- **VIX (Volatility Index)**: Adjusts trading signal thresholds
  - High VIX → more conservative (higher thresholds)
  - Low VIX → more aggressive (lower thresholds)
- **S&P 500 Index**: Used for beta calculation
- **Beta**: Measures stock correlation with market

### 4. Maximum Fan-Out Visibility
- Orchestrator → 10 symbol flows → 240 time partition flows
- Each partition visible as separate flow run in Prefect UI
- Clear graph showing complete dependency tree

### 5. Granular Reprocessing
- Can rerun specific contract+timestamp combinations
- Use `analyze-time-partition` deployment with exact parameters
- Example: Reprocess AAPL at 2024-01-02 09:30 only

### 6. Portfolio-Level Analytics
- Cross-contract aggregation
- Sharpe ratio calculation
- Win rate analysis
- Time series performance tracking

## Deployment Configuration

All 6 deployments configured in `prefect.yaml`:

1. **ingest-market-data**: Standalone or triggered by orchestrator
2. **validate-data**: Standalone or triggered by orchestrator
3. **orchestrator**: Main entry point for full pipeline
4. **analyze-symbol**: Triggered by orchestrator (one per contract)
5. **analyze-time-partition**: Triggered by symbol flows (one per timestamp)
6. **aggregate-portfolio**: Standalone, run after orchestrator completes

## Usage Examples

### Full Pipeline with Validation
```bash
# Run complete pipeline with pre-existing data
prefect deployment run trading-orchestrator/orchestrator \
  --param num_contracts=10 \
  --param run_validation=true \
  --param run_ingestion=false
```

### With Live Data Ingestion
```bash
# Fetch live data and process
prefect deployment run trading-orchestrator/orchestrator \
  --param num_contracts=5 \
  --param run_ingestion=true \
  --param run_validation=true \
  --param ingestion_symbols='["AAPL","MSFT","GOOGL","AMZN","TSLA"]' \
  --param ingestion_start_date="2024-10-15" \
  --param ingestion_end_date="2024-10-18"
```

### Reprocess Single Symbol
```bash
# Reanalyze one contract across all timestamps
prefect deployment run analyze-symbol/analyze-symbol \
  --param contract="AAPL"
```

### Reprocess Single Partition
```bash
# Reanalyze specific contract at specific time
prefect deployment run analyze-time-partition/analyze-time-partition \
  --param contract="AAPL" \
  --param timestamp="2024-01-02T09:30:00-05:00"
```

### Standalone Portfolio Aggregation
```bash
# Run analytics on existing results
prefect deployment run aggregate-portfolio/aggregate-portfolio \
  --param output_dir="s3://se-demo-raw-data-files/trading-results"
```

## Generated Data Files

### Input Data (with market indices)
```
input/
  ├── spx_holdings_hourly.parquet      # Stock prices (10 contracts × 24 timestamps)
  ├── vix_hourly.parquet                # Volatility index (24 timestamps)
  └── spx_hourly.parquet                # S&P 500 index (24 timestamps)
```

Generate with:
```bash
cd input
python generate_hourly_data.py
```

### Output Structure
```
output/trading-results/
  ├── AAPL/
  │   ├── 20240102_093000.parquet
  │   ├── 20240102_103000.parquet
  │   └── ...
  ├── MSFT/
  │   └── ...
  └── [other contracts]
```

## Prefect UI Artifacts

Each layer creates detailed artifacts:

1. **Ingestion**: Data source summary with symbol counts
2. **Validation**: Quality report with issues table
3. **Orchestrator**: Pipeline overview with architecture diagram
4. **Symbol**: Per-contract summary with timestamps
5. **Time Partition**: (Minimal - data in result)
6. **Aggregation**: 
   - Portfolio summary markdown
   - Contract performance table
   - Time series performance table

## Performance Characteristics

With default settings (10 contracts, 24 timestamps):
- **Total flows triggered**: 241 (1 orchestrator + 10 symbols + 240 partitions + 1 validation)
- **Parallel K8s jobs**: Up to 240 (time partitions run in parallel)
- **Processing pattern**: Wide fan-out for maximum parallelism

## Next Steps

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Generate sample data**:
   ```bash
   cd input
   python generate_hourly_data.py
   ```

3. **Deploy to Prefect**:
   ```bash
   prefect deploy --all
   ```

4. **Run the pipeline**:
   ```bash
   prefect deployment run trading-orchestrator/orchestrator
   ```

5. **View results in Prefect UI**:
   - Navigate to flow runs to see the multi-layer graph
   - Check artifacts for detailed analytics
   - Explore the fan-out pattern

## Architecture Benefits

✅ **Realistic**: Live data, validation, market context  
✅ **Visible**: Every partition is a separate flow run  
✅ **Flexible**: Reprocess any granularity level  
✅ **Scalable**: Massive parallelism via K8s  
✅ **Production-ready**: Quality gates, error handling, retry logic  
✅ **Comprehensive**: End-to-end pipeline with analytics  

