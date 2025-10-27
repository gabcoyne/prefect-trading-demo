# Deployment Guide

Step-by-step guide to deploy the Trading Partition Demo to Prefect Cloud with K8s.

## Prerequisites

- ✅ Prefect Cloud account with workspace configured
- ✅ AWS account with S3 access
- ✅ Docker installed and configured
- ✅ K8s work pool named `demo_eks` created in Prefect Cloud
- ✅ AWS ECR access to `455346737763.dkr.ecr.us-east-2.amazonaws.com`

## Step 1: Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or install manually
uv pip install -e .
```

## Step 2: Upload Data to S3

Upload the parquet data file to S3 so it's accessible by K8s jobs:

```bash
uv run python scripts/upload_data_to_s3.py
```

This uploads `spx_holdings_hourly.parquet` to `s3://se-demo-raw-data-files/`.

## Step 3: Configure Prefect Authentication

Set your Prefect Cloud credentials:

```bash
# Login to Prefect Cloud
prefect cloud login

# Or set API key directly
export PREFECT_API_URL="https://api.prefect.cloud/api/accounts/[ACCOUNT_ID]/workspaces/[WORKSPACE_ID]"
export PREFECT_API_KEY="your-api-key"
```

## Step 4: Setup S3 Blocks (Optional)

Create Prefect S3 blocks for result storage:

```bash
uv run python scripts/setup_s3_blocks.py
```

## Step 5: Create ECR Repository

First time setup - create the ECR repository:

```bash
uv run python scripts/create_ecr_repo.py
```

This creates the `se-demos/trading-partition-demo` repository in ECR.

**Note**: Only needed once. Skip if repository already exists.

## Step 6: Authenticate with ECR

Ensure Docker can push to ECR:

```bash
# Login to ECR
aws ecr get-login-password --region us-east-2 | \
  docker login --username AWS --password-stdin \
  455346737763.dkr.ecr.us-east-2.amazonaws.com
```

## Step 6: Deploy to Prefect Cloud

Deploy both the parent and child flows. This will automatically:
- Build the Docker image for linux/amd64
- Push it to ECR
- Register both deployments

```bash
prefect deploy --all
```

This creates two deployments:
- `trading-partition-demo/orchestrator` - Parent orchestrator
- `trading-partition-demo/analyze-contract` - Child per-contract analysis

**Note**: The build step uses `prefect-docker` to automatically build and push the image. No manual Docker commands needed!

## Step 7: Run the Orchestrator

### Option A: Via Prefect UI
1. Go to Prefect Cloud UI
2. Navigate to Deployments
3. Find `trading-partition-demo/orchestrator`
4. Click "Run" → "Quick Run"

### Option B: Via CLI
```bash
prefect deployment run trading-partition-demo/orchestrator
```

### Option C: With Custom Parameters
```bash
prefect deployment run trading-partition-demo/orchestrator \
  --param num_contracts=20 \
  --param parquet_path=s3://se-demo-raw-data-files/spx_holdings_hourly.parquet
```

## Step 8: Monitor Execution

Watch the flows execute in Prefect Cloud:

```bash
# Watch flow runs
prefect flow-run ls --limit 20

# Follow logs for a specific run
prefect flow-run logs <flow-run-id> --follow
```

Or use the Prefect UI to:
- View flow run graph
- Filter by tags (`contract:AAPL`, `time_slice:10`)
- Check artifacts and assets
- Monitor K8s job execution

## Verification

After the orchestrator completes:

1. **Check S3 for Results**:
```bash
aws s3 ls s3://se-demo-raw-data-files/trading-results/
```

You should see files like:
- `AAPL_analysis.parquet`
- `MSFT_analysis.parquet`
- etc.

2. **Check Prefect Assets**:
Go to Prefect UI → Assets to see materialized data products.

3. **Check Artifacts**:
Go to Prefect UI → Artifacts to see trade analysis summaries.

## Troubleshooting

### Issue: Child flows not running
- Verify the child deployment name matches: `trading-partition-demo/analyze-contract`
- Check work pool is active: `prefect work-pool ls`
- Verify K8s worker is running

### Issue: S3 access denied
- Check AWS credentials are configured in K8s
- Verify S3 bucket policy allows access
- Ensure IAM role has S3 read/write permissions

### Issue: ECR repository not found
- Create the repository: `uv run python scripts/create_ecr_repo.py`
- Verify it exists in AWS Console → ECR

### Issue: Docker build failed during deploy
- Ensure Docker daemon is running
- Verify ECR login credentials are valid
- Check `prefect-docker` is installed: `uv pip install prefect-docker`

### Issue: Docker image pull failed in K8s
- Verify ECR repository exists
- Check image was pushed successfully
- Ensure K8s has ECR pull credentials

### Issue: Import errors in flows
- Check `pyproject.toml` includes all required packages
- Redeploy: `prefect deploy --all` to rebuild image
- Verify base image in Dockerfile is correct

## Customization

### Process More Contracts
Edit `prefect.yaml` and change `num_contracts`:

```yaml
parameters:
  num_contracts: 50  # Process 50 contracts instead of 10
```

### Change Output Location
Edit `prefect.yaml` and update `output_dir`:

```yaml
parameters:
  output_dir: "s3://your-bucket/your-path"
```

### Adjust K8s Resources
Edit `prefect.yaml` and add resource limits:

```yaml
job_variables:
  image: "..."
  resources:
    limits:
      cpu: "2"
      memory: "4Gi"
    requests:
      cpu: "1"
      memory: "2Gi"
```

## Next Steps

- Schedule regular runs
- Add more sophisticated trading algorithms
- Integrate with downstream analytics
- Scale to all 418 contracts
- Add alerting for trade quality metrics

