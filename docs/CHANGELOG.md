# Changelog

## Issues Fixed

### ✅ Parameter Size Limit Exceeded
**Problem**: Passing all 28,048 timestamps as a `time_slices` parameter caused 422 errors due to parameter size limits.

**Solution**: Removed `time_slices` parameter. Child flows now load all data directly from the parquet file.

**Changes**:
- `flows/orchestrator_flow.py`: Removed time_slices from trigger function
- `flows/analyze_contract_flow.py`: Updated to load all contract data from parquet
- `prefect.yaml`: Removed time_slices from deployment parameters

### ✅ Excessive Logging
**Problem**: Too much output from Prefect logs made it difficult to see results.

**Solution**: Added `log_prints=False` to all tasks and flows, set default logging level to WARNING.

**Changes**:
- All `@task` and `@flow` decorators: Added `log_prints=False`
- `run_demo.py`: Sets `PREFECT_LOGGING_LEVEL=WARNING`
- `docs/QUICKSTART.md`: Documented environment variable

### ✅ Deployment Name Mismatch
**Problem**: Calling wrong deployment name format (used project name instead of flow name).

**Solution**: Updated to use correct format: `{flow_name}/{deployment_name}`.

**Changes**:
- Updated all references from `trading-partition-demo/analyze-contract` to `analyze-contract/analyze-contract`

### ✅ Artifact Key Validation
**Problem**: Artifact keys with uppercase letters (`AAPL-analysis-summary`) failed validation.

**Solution**: Convert contract to lowercase for artifact keys.

**Changes**:
- `flows/analyze_contract_flow.py`: Use `contract.lower()` for artifact keys

### ✅ Pandas FutureWarning
**Problem**: `pct_change()` deprecated default `fill_method='pad'`.

**Solution**: Explicitly set `fill_method=None`.

**Changes**:
- `flows/analyze_contract_flow.py`: `pct_change(fill_method=None)`

### ✅ Package Build Configuration
**Problem**: Hatchling couldn't determine which files to include in the wheel.

**Solution**: Added explicit package configuration.

**Changes**:
- `pyproject.toml`: Added `[tool.hatch.build.targets.wheel]` with `packages = ["flows", "scripts"]`

### ✅ Automated Docker Build
**Problem**: Manual Docker build steps were error-prone and inconvenient.

**Solution**: Configured `prefect deploy` to automatically build and push Docker images.

**Changes**:
- `prefect.yaml`: Added `build_docker_image` and `push_docker_image` steps
- `pyproject.toml`: Added `prefect-docker` dependency
- Updated all documentation to reflect automated workflow

### ✅ File Not Found in K8s
**Problem**: Child flows running in K8s couldn't find local parquet file path.

**Solution**: Updated orchestrator to use S3 paths when triggering child flows.

**Changes**:
- `run_demo.py`: Changed to use S3 paths for parquet_path and output_dir

### ✅ S3 Access Denied in K8s
**Problem**: K8s pods couldn't access S3 bucket due to missing IAM permissions.

**Solution**: Configure IAM role at work pool level in Prefect Cloud UI. The `demo_eks` work pool should be configured with appropriate service account that has S3 access via IRSA.

## Current Status

### Working Features
- ✅ Parent orchestrator triggers child flows successfully
- ✅ Child flows process all timestamps for each contract
- ✅ Artifacts created with proper lowercase keys
- ✅ Minimal logging output
- ✅ Automated Docker build and push via `prefect deploy`
- ✅ Deployments registered and callable

### Test Results
- Local test (single contract AAPL): **Success** 
  - Processed 28,048 timestamps
  - 3,141 good trades, 238 bad trades
  - 92.74% success rate
- Orchestrator: **Success**
  - Triggered 10 child flows
  - All flows scheduled in Prefect Cloud

### Next Steps for Users
1. Create ECR repository (if needed)
2. Upload data to S3
3. Authenticate with ECR
4. Run `prefect deploy --all`
5. Monitor in Prefect Cloud UI

