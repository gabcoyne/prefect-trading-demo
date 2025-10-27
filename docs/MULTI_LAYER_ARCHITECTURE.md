# Trading Pipeline Architecture

## Overview

This demo showcases a streamlined trading pipeline built with Prefect. The architecture demonstrates parallel execution patterns, market context enrichment, and contract-level analysis.

## Architecture Layers

### 2-Layer Deployment Structure

```
1. Main Orchestrator Flow (orchestrator)
   └─> Coordinates entire pipeline
   
2. Symbol Flows (analyze-symbol) [N parallel instances]
   └─> One per contract/stock, processes all timestamps
```

## Flow Hierarchy

### Level 1: Main Orchestrator
**File**: `flows/orchestrator_flow.py`

Top-level coordinator for the entire pipeline:
1. Loads and partitions contract data from S3
2. Triggers symbol flows in parallel
3. Creates comprehensive orchestration artifact

**Configuration Options**:
- `num_contracts`: Limit contracts for demo (default: 10)

### Level 2: Symbol Flow
**File**: `flows/analyze_symbol_flow.py`

Analyzes a single contract across all timestamps:
1. **Load**: Loads contract data with VIX and SPX from S3
2. **Calculate**: 
   - Beta (correlation with S&P 500) for each timestamp
   - Volatility-adjusted trading signals
   - Higher VIX → more conservative thresholds
3. **Analyze**: 
   - Generates buy/sell signals
   - Evaluates trade quality
4. **Save**: Stores complete analysis results

**Market Context Enrichment**:
- Beta calculation vs S&P 500
- VIX-based signal adjustment
- Dynamic buy/sell thresholds
- Trade quality evaluation

## Data Flow

```
S3 Storage (Stock Data, VIX, SPX parquet files)
    ↓
[Orchestrator] → Loads data, triggers N Symbol Flows in parallel
    ↓
[Symbol Flow × N] → Each analyzes all timestamps for one contract
    ↓
Results saved to S3 or local output directory
```

## Key Features

### 1. Market Context Enrichment
- **VIX (Volatility Index)**: Adjusts trading signal thresholds
  - High VIX → more conservative (higher thresholds)
  - Low VIX → more aggressive (lower thresholds)
- **S&P 500 Index**: Used for beta calculation
- **Beta**: Measures stock correlation with market

### 2. Parallel Execution
- Orchestrator → N symbol flows in parallel
- Each symbol flow processes all timestamps for its contract
- Efficient fan-out pattern for large-scale analysis

### 3. Flexible Output
- K8s environment: outputs to S3
- Local environment: outputs to local directory
- All input data always pulled from S3

## Deployment Configuration

Two deployments configured in `prefect.yaml`:

1. **orchestrator**: Main entry point for full pipeline
2. **analyze-symbol**: Triggered by orchestrator (one per contract)

## Usage Examples

### Run Full Pipeline
```bash
# Process 10 contracts in parallel
prefect deployment run trading-orchestrator/orchestrator \
  --param num_contracts=10
```

### Analyze Single Symbol
```bash
# Reanalyze one contract across all timestamps
prefect deployment run analyze-symbol/analyze-symbol \
  --param contract="AAPL"
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

The pipeline creates rich artifacts:

1. **Orchestrator**: Pipeline overview with architecture diagram and processing scope
2. **Symbol**: Per-contract analysis results stored in parquet files

## Performance Characteristics

With default settings (10 contracts, ~28K timestamps each):
- **Total flows triggered**: 11 (1 orchestrator + 10 symbol flows)
- **Parallel K8s jobs**: Up to 10 (symbol flows run in parallel)
- **Processing pattern**: Efficient fan-out for parallel symbol analysis

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

✅ **Market Context**: VIX and S&P 500 integration for realistic trading signals  
✅ **Parallel Execution**: N symbol flows run concurrently on K8s  
✅ **Flexible**: Reprocess individual contracts or full pipeline  
✅ **Scalable**: Efficient parallelism via K8s work pool  
✅ **S3-backed**: All input data pulled from S3 for consistency  
✅ **Cloud-native**: Designed for production K8s deployments  

