# Architecture

Detailed architecture documentation for the Trading Partition Demo.

## System Overview

The Trading Partition Demo implements a parent-child flow pattern where a single orchestrator spawns hundreds of parallel child flows, each processing algorithmic trading analysis for a specific stock contract.

```
┌─────────────────────────────────────────────────────────────┐
│                    Parent Orchestrator                       │
│              (trading_orchestrator flow)                     │
│                                                              │
│  1. Read spx_holdings_hourly.parquet                        │
│  2. Extract 418 contracts                                      │
│  3. Prepare 24 hourly time slices                           │
│  4. Spawn child flows via run_deployment()                  │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ├─────> Child Flow (Contract: AAPL)
                   ├─────> Child Flow (Contract: MSFT)
                   ├─────> Child Flow (Contract: GOOGL)
                   ├─────> ... (parallel K8s jobs)
                   └─────> Child Flow (Contract: XYZ)
                           │
                           ├─ Task A: Load Data
                           ├─ Task B: Analyze Trades
                           └─ Task C: Save Results
                                    ↓
                           s3://.../AAPL_analysis.parquet
```

## Data Flow

### Input Data
- **Source**: `spx_holdings_hourly.parquet` 
- **Location**: S3 bucket `se-demo-raw-data-files`
- **Format**: Parquet with timestamp index
- **Dimensions**: 28,048 rows × 419 columns
  - 418 stock contracts (AAPL, MSFT, etc.)
  - 1 index column (SPX)
  - Date range: 01/27/2000 - 12/20/2013
  - 8 hourly timestamps per trading day

### Processing Pipeline

#### Parent Flow: `trading_orchestrator`
1. **Load & Partition** (Task)
   - Read parquet file from S3
   - Extract contract list (column names)
   - Count total timestamps for reporting
   - Apply `num_contracts` limit for demo

2. **Trigger Children** (Task per contract)
   - Call `run_deployment()` for each contract
   - Pass parameters: contract, parquet_path, output_dir
   - Non-blocking execution (timeout=0)
   - Collect flow run metadata
   - Note: Time slices not passed (child loads all data)

3. **Report** (Artifact)
   - Create markdown artifact with summary
   - List all triggered flow runs
   - Display contract count and time slice info

#### Child Flow: `analyze_contract`
Each child flow processes one contract through three sequential tasks:

**Task A: Load & Prepare**
- Input: Parquet path, contract
- Process: Load all historical data for the contract
- Output: DataFrame with price data for all timestamps
- Asset: `{contract}_raw_data`

**Task B: Analyze Trades**
- Input: Contract DataFrame
- Process: 
  - Calculate price changes
  - Generate buy/sell signals (momentum strategy)
  - Evaluate trade quality
- Output: DataFrame with signals and quality scores
- Asset: `{contract}_trade_signals`

**Task C: Aggregate & Save**
- Input: Analyzed DataFrame, output directory
- Process:
  - Calculate summary statistics
  - Create Prefect artifact (table)
  - Save to parquet file
- Output: S3 path to saved file
- Asset: `{contract}_analysis`

### Output Data
- **Location**: `s3://se-demo-raw-data-files/trading-results/`
- **Format**: Per-contract parquet files
- **Naming**: `{contract}_analysis.parquet`
- **Contents**:
  - Timestamp
  - Price and price changes
  - Trade signals (buy/sell/hold)
  - Trade quality (good/bad/neutral)
  - Summary statistics

## Deployment Architecture

### Container Image
- **Base**: `python:3.11-slim`
- **Registry**: AWS ECR
- **Image**: `455346737763.dkr.ecr.us-east-2.amazonaws.com/se-demos/trading-partition-demo:latest`
- **Contents**: Flows, scripts, dependencies
- **Build**: Automated via `prefect deploy` using `prefect-docker`

### K8s Execution
- **Work Pool**: `demo_eks` (pre-configured)
- **Job per Flow**: Each child flow runs in separate K8s job
- **Parallelism**: Limited by work pool concurrency
- **Resources**: Configurable via job_variables

### Prefect Deployments

**Parent Deployment**: `trading-partition-demo/orchestrator`
- Entrypoint: `flows/orchestrator_flow.py:trading_orchestrator`
- Tags: `orchestrator`, `parent`
- Parameters: `num_contracts`, `parquet_path`, `output_dir`
- Schedule: None (manual trigger)

**Child Deployment**: `trading-partition-demo/analyze-contract`
- Entrypoint: `flows/analyze_contract_flow.py:analyze_contract`
- Tags: `child`, `contract-analysis`
- Parameters: `contract`, `time_slices`, `parquet_path`, `output_dir`
- Schedule: None (triggered by parent)

## Partitioning Strategy

### Contract-Based Partitioning
- **Primary Dimension**: Stock contract
- **Partition Count**: 418 (or limited for demo)
- **Benefits**:
  - Independent processing per contract
  - Partial completion (99 contracts succeed even if 1 fails)
  - Clear observability (filter by `contract:AAPL` tag)

### Time Slice Processing
- **Secondary Dimension**: Hourly timestamps
- **Slices per Contract**: 24 (configurable)
- **Processing**: Sequential within each contract
- **Benefits**:
  - Maintain time ordering for trade analysis
  - Support for cross-time dependencies
  - Granular progress tracking

## Trading Algorithm

### Momentum Strategy
Simple algorithmic trading approach demonstrating the platform:

1. **Signal Generation**
   - Calculate hourly price change percentage
   - Buy signal: price increase > 0.5%
   - Sell signal: price decrease < -0.5%
   - Hold: otherwise

2. **Quality Evaluation**
   - Good trade: Signal matches subsequent price movement
     - Buy → price goes up
     - Sell → price goes down
   - Bad trade: Signal contradicts subsequent movement
     - Buy → price goes down
     - Sell → price goes up
   - Neutral: Hold position or last time slice

3. **Metrics**
   - Total trades executed
   - Good vs bad trade count
   - Success rate percentage

## Observability Features

### Tags
- Flow-level: `contract:AAPL`, `time_slice:10`, etc.
- Task-level: Inherited from flow
- Usage: Filter runs in Prefect UI

### Artifacts
- Table artifacts per contract with summary statistics
- Markdown artifact from orchestrator with run overview
- Viewable in Prefect UI Artifacts tab

### Assets
- `{contract}_raw_data`: Loaded price data
- `{contract}_trade_signals`: Generated trading signals
- `{contract}_analysis`: Final analysis output
- Tracked in Prefect UI Assets tab

### Flow Run Names
- Parent: `orchestrator-{num_contracts}-contracts`
- Child: `analyze-{contract}`
- Benefits: Quick identification in UI

### Result Persistence
- Location: `s3://se-demo-raw-data-files/prefect_results/`
- All flow results persisted to S3
- Accessible for downstream processing

## Scalability Considerations

### Current Demo Scale
- 10 contracts (configurable)
- 24 time slices per contract
- ~240 total work items
- Sequential execution of 3 tasks per contract

### Production Scale
- 418 contracts (all SPX holdings)
- 28,048 time slices available
- Can process all historical data
- Parallel K8s jobs limited by work pool

### Future Enhancements
- Dynamic time slice partitioning
- Cross-contract dependencies
- Real-time data ingestion
- Advanced trading algorithms
- Multi-strategy comparison

