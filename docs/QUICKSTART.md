# Quick Start Guide

Get up and running with the Trading Partition Demo in minutes.

## Prerequisites

- AWS credentials configured
- Prefect Cloud account (logged in)
- Docker running
- `uv` installed

### Environment Variables

For reduced logging output, set:
```bash
export PREFECT_LOGGING_LEVEL=WARNING
```

## Deploy in 5 Steps

### 1. Install Dependencies

```bash
uv sync
```

### 2. Create ECR Repository

First time only - create the ECR repository:

```bash
uv run python scripts/create_ecr_repo.py
```

This creates `se-demos/trading-partition-demo` in ECR.

### 3. Upload Data to S3

```bash
uv run python scripts/upload_data_to_s3.py
```

### 4. Authenticate with ECR

```bash
aws ecr get-login-password --region us-east-2 | \
  docker login --username AWS --password-stdin \
  455346737763.dkr.ecr.us-east-2.amazonaws.com
```

**Note**: This token expires after 12 hours. Re-run if you get auth errors.

### 5. Deploy

```bash
uv run prefect deploy --all
```

This will automatically:
- Build Docker image for linux/amd64
- Push to ECR
- Register both deployments

## Run

### Via CLI

```bash
uv run prefect deployment run trading-partition-demo/orchestrator
```

### Via UI

1. Go to Prefect Cloud
2. Navigate to Deployments
3. Click `trading-partition-demo/orchestrator`
4. Click "Run"

## Monitor

Watch in Prefect Cloud:
- Flow runs tab
- Filter by tags: `contract:AAPL`, `time_slice:10`
- View artifacts for trade summaries
- Check assets for materialized data

## Troubleshooting

### ECR Repository Not Found
```bash
# Create the repository first
uv run python scripts/create_ecr_repo.py
```

### ECR Auth Expired
```bash
# Re-authenticate
aws ecr get-login-password --region us-east-2 | \
  docker login --username AWS --password-stdin \
  455346737763.dkr.ecr.us-east-2.amazonaws.com
```

### Prefect Not Authenticated
```bash
prefect cloud login
```

### AWS Credentials Missing
```bash
# Set credentials
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_SESSION_TOKEN="..."  # if using temporary credentials
```

## After Making Code Changes

If you modify the flow code, redeploy to rebuild the Docker image:

```bash
# Ensure ECR auth is valid
aws ecr get-login-password --region us-east-2 | \
  docker login --username AWS --password-stdin \
  455346737763.dkr.ecr.us-east-2.amazonaws.com

# Redeploy (rebuilds image with latest code)
uv run prefect deploy --all
```

## Next Steps

- See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed guide
- See [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- See [ALGORITHM.md](ALGORITHM.md) for trading strategy
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues

