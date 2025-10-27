# Troubleshooting Guide

Common issues and solutions for the Trading Partition Demo.

## Deployment Issues

### FileNotFoundError in K8s

**Error**: `FileNotFoundError: [Errno 2] No such file or directory: 'spx_holdings_hourly.parquet'`

**Cause**: Child flows are receiving a local file path instead of S3 path.

**Solutions**:
1. Ensure orchestrator is called with S3 paths:
   ```python
   trading_orchestrator(
       parquet_path="s3://se-demo-raw-data-files/spx_holdings_hourly.parquet",
       output_dir="s3://se-demo-raw-data-files/trading-results"
   )
   ```

2. Verify data was uploaded to S3:
   ```bash
   aws s3 ls s3://se-demo-raw-data-files/spx_holdings_hourly.parquet
   ```

3. If missing, upload:
   ```bash
   uv run python scripts/upload_data_to_s3.py
   ```

### Deployment Not Found

**Error**: `ObjectNotFound: Deployment not found`

**Cause**: Either deployments aren't registered or wrong deployment name is being used.

**Solutions**:
1. Check deployed names:
   ```bash
   uv run prefect deployment ls | grep -E "analyze-contract|trading-orchestrator"
   ```

2. Expected names:
   - `analyze-contract/analyze-contract` (child)
   - `trading-orchestrator/orchestrator` (parent)

3. Redeploy if needed:
   ```bash
   uv run prefect deploy --all
   ```

### Code Changes Not Reflected

**Error**: Old code behavior persists after making changes.

**Cause**: Docker image wasn't rebuilt with latest code.

**Solution**: Redeploy to trigger rebuild:
```bash
# Authenticate if needed
aws ecr get-login-password --region us-east-2 | \
  docker login --username AWS --password-stdin \
  455346737763.dkr.ecr.us-east-2.amazonaws.com

# Redeploy (rebuilds image automatically)
uv run prefect deploy --all
```

### ECR Repository Not Found

**Error**: `name unknown: The repository with name 'se-demos/trading-partition-demo' does not exist`

**Solution**: Create the ECR repository:
```bash
uv run python scripts/create_ecr_repo.py
```

### ECR Auth Expired

**Error**: `denied: Your authorization token has expired`

**Solution**: Re-authenticate (tokens expire after 12 hours):
```bash
aws ecr get-login-password --region us-east-2 | \
  docker login --username AWS --password-stdin \
  455346737763.dkr.ecr.us-east-2.amazonaws.com
```

## Runtime Issues

### Excessive Logging

**Problem**: Too much output from Prefect logs.

**Solution**: Set logging level to WARNING:
```bash
export PREFECT_LOGGING_LEVEL=WARNING
uv run python run_demo.py
```

### S3 Access Denied in K8s

**Error**: `AWS Error ACCESS_DENIED during HeadObject operation`

**Cause**: K8s pods don't have IAM permissions to access S3 bucket.

**Solutions**:

**Option 1: Configure K8s Service Account with IAM Role (Recommended)**
1. Create IAM role with S3 read/write policy for `se-demo-raw-data-files`
2. Associate IAM role with K8s service account via IRSA (IAM Roles for Service Accounts)
3. Update work pool to use the service account

**Option 2: Use AWS Credentials Block**
1. Create Prefect AWS Credentials block in Prefect Cloud UI
2. Reference it in your flows (see below)

**Option 3: Environment Variables in Work Pool**
Add AWS credentials to K8s job variables in `prefect.yaml`:
```yaml
job_variables:
  image: "{{ build-image.image }}"
  env:
    AWS_ACCESS_KEY_ID: "{{ prefect.variables.aws_access_key_id }}"
    AWS_SECRET_ACCESS_KEY: "{{ prefect.variables.aws_secret_access_key }}"
    AWS_DEFAULT_REGION: "us-east-2"
```

Then create Prefect variables:
```bash
prefect variable set aws_access_key_id YOUR_KEY
prefect variable set aws_secret_access_key YOUR_SECRET --overwrite
```

**Note**: Option 1 (IRSA) is most secure for production use.

### S3 Access Denied Locally

**Error**: `Unable to locate credentials` or `Access Denied`

**Solutions**:
1. Check AWS credentials:
   ```bash
   aws sts get-caller-identity
   ```

2. Verify S3 bucket permissions:
   ```bash
   aws s3 ls s3://se-demo-raw-data-files/
   ```

3. Configure AWS credentials:
   ```bash
   aws configure
   # Or set environment variables
   export AWS_ACCESS_KEY_ID="..."
   export AWS_SECRET_ACCESS_KEY="..."
   export AWS_DEFAULT_REGION="us-east-2"
   ```

### Parameter Too Large (422 Error)

**Error**: `422 Unprocessable Entity` with large parameter data

**Cause**: Passing too much data (like all timestamps) as parameters.

**Solution**: Already fixed - child flows now load data directly from S3 instead of receiving it as a parameter.

### Artifact Key Validation Error

**Error**: `Artifact key must only contain lowercase letters, numbers, and dashes`

**Cause**: Using uppercase contracts in artifact keys.

**Solution**: Already fixed - artifact keys use `contract.lower()`.

## Testing Issues

### Deployments Required for run_demo.py

**Problem**: `run_demo.py` fails because deployments don't exist.

**Solution**: Use local test scripts instead:
```bash
# Test single contract (no deployments needed)
uv run python scripts/test_local.py

# Test multiple contracts (no deployments needed)
uv run python scripts/test_local_full.py
```

### Import Errors

**Error**: `Import "prefect" could not be resolved`

**Solution**: Install dependencies:
```bash
uv sync
```

## K8s Worker Issues

### Worker Not Running

**Problem**: Child flows scheduled but not executing.

**Solutions**:
1. Check work pool status:
   ```bash
   uv run prefect work-pool ls
   ```

2. Verify worker is running in K8s cluster

3. Check worker logs in Prefect Cloud UI

### Image Pull Errors

**Error**: `ImagePullBackOff` or `ErrImagePull` in K8s

**Solutions**:
1. Verify image exists in ECR:
   ```bash
   aws ecr describe-images \
     --repository-name se-demos/trading-partition-demo \
     --region us-east-2
   ```

2. Check K8s has ECR pull credentials

3. Verify image name in `prefect.yaml` matches ECR repository

## Data Issues

### Contract Not Found

**Error**: `KeyError: 'SYMBOL_NAME'`

**Cause**: Contract doesn't exist in parquet file.

**Solution**: Check available contracts:
```python
import pandas as pd
df = pd.read_parquet("spx_holdings_hourly.parquet")
print(df.columns.tolist())
```

### Empty Results

**Problem**: No trades generated for a contract.

**Cause**: Price volatility might be too low for thresholds (±0.5%).

**Solution**: Adjust thresholds in `flows/analyze_contract_flow.py`:
```python
# Lower thresholds for more trades
df.loc[df['price_change_pct'] > 0.1, 'signal'] = 'buy'  # was 0.5
df.loc[df['price_change_pct'] < -0.1, 'signal'] = 'sell'  # was -0.5
```

## Getting Help

If you encounter other issues:

1. Check Prefect Cloud logs for detailed error messages
2. View worker logs via the work pool page
3. Verify deployment parameters match expected S3 paths
4. Test locally first with `scripts/test_local.py`
5. Check [Changelog](CHANGELOG.md) for recent fixes

