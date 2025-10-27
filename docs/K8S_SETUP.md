# Kubernetes Setup Guide

Configuration needed for K8s deployment with S3 access.

## Prerequisites

- EKS cluster with `demo_eks` work pool configured
- S3 bucket: `se-demo-raw-data-files`
- ECR access for pulling Docker images

## S3 Access Configuration

### Option 1: IRSA (IAM Roles for Service Accounts) - Recommended

This is the most secure approach for production.

#### 1. Create IAM Policy

Create a policy for S3 access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::se-demo-raw-data-files/*",
        "arn:aws:s3:::se-demo-raw-data-files"
      ]
    }
  ]
}
```

#### 2. Create IAM Role with OIDC Trust

```bash
# Create role for service account
eksctl create iamserviceaccount \
  --name prefect-worker-sa \
  --namespace default \
  --cluster your-cluster-name \
  --attach-policy-arn arn:aws:iam::455346737763:policy/PrefectS3Access \
  --approve
```

#### 3. Update Work Pool Configuration

In Prefect Cloud UI → Work Pools → demo_eks:
- Add `serviceAccountName: prefect-worker-sa` to job template

Or in code, update `prefect.yaml`:
```yaml
job_variables:
  image: "{{ build-image.image }}"
  service_account_name: "prefect-worker-sa"  # or "read-only-s3" if already exists
```

**Note**: This project already uses `read-only-s3` service account in `prefect.yaml`.

### Option 2: AWS Credentials via Environment Variables

Less secure but simpler for demos.

#### 1. Create Prefect Variables

```bash
prefect variable set aws_access_key_id YOUR_ACCESS_KEY
prefect variable set aws_secret_access_key YOUR_SECRET_KEY --overwrite
```

#### 2. Update prefect.yaml

```yaml
job_variables:
  image: "{{ build-image.image }}"
  env:
    AWS_ACCESS_KEY_ID: "{{ prefect.variables.aws_access_key_id }}"
    AWS_SECRET_ACCESS_KEY: "{{ prefect.variables.aws_secret_access_key }}"
    AWS_DEFAULT_REGION: "us-east-2"
```

#### 3. Redeploy

```bash
uv run prefect deploy --all
```

### Option 3: AWS Credentials Block

Use Prefect AWS Credentials block for centralized credential management.

#### 1. Create in Prefect UI

Navigate to:  
Blocks → + → AWS Credentials

Fill in:
- Block Name: `trading-demo-aws-creds`
- AWS Access Key ID: Your key
- AWS Secret Access Key: Your secret
- AWS Session Token: (if using temporary creds)
- Region: `us-east-2`

#### 2. Update Flow Code

Modify `flows/analyze_contract_flow.py`:

```python
from prefect_aws import AwsCredentials

@task(tags=["load"], log_prints=False)
def load_contract_data(contract: str, parquet_path: str):
    # Load AWS credentials
    aws_creds = AwsCredentials.load("trading-demo-aws-creds")
    
    # Use with pandas
    storage_options = aws_creds.get_boto3_session().get_credentials().__dict__
    df = pd.read_parquet(parquet_path, storage_options=storage_options)
    # ... rest of code
```

## ECR Access Configuration

### For K8s to Pull Images

#### 1. Create Secret for ECR

```bash
kubectl create secret docker-registry ecr-secret \
  --docker-server=455346737763.dkr.ecr.us-east-2.amazonaws.com \
  --docker-username=AWS \
  --docker-password=$(aws ecr get-login-password --region us-east-2)
```

**Note**: This token expires after 12 hours. For production, use:
- ECR credential helper
- IRSA with ECR permissions
- Image pull secrets with automatic refresh

#### 2. Update Work Pool

Add imagePullSecrets to work pool job template:
```yaml
imagePullSecrets:
  - name: ecr-secret
```

## Verification

### Test S3 Access from Pod

```bash
# Create test pod
kubectl run aws-test --image=amazon/aws-cli --rm -it -- \
  s3 ls s3://se-demo-raw-data-files/

# If using IRSA, should work without credentials
# If not, you'll see ACCESS_DENIED
```

### Check Service Account

```bash
# View service account
kubectl get sa prefect-worker-sa -o yaml

# Check annotation for IAM role
kubectl get sa prefect-worker-sa -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}'
```

### Test ECR Pull

```bash
# Check if image pull secret exists
kubectl get secrets | grep ecr

# Test pulling image
kubectl run test-pull --image=455346737763.dkr.ecr.us-east-2.amazonaws.com/se-demos/trading-partition-demo:latest --rm -it
```

## Recommended Production Setup

1. **IRSA for S3 Access**
   - Service account with IAM role
   - Automatic credential rotation
   - No secrets to manage

2. **ECR with IRSA**
   - IAM role includes ECR pull permissions
   - No manual secret management

3. **Resource Limits**
   ```yaml
   job_variables:
     resources:
       limits:
         cpu: "2"
         memory: "4Gi"
       requests:
         cpu: "1"
         memory: "2Gi"
   ```

4. **Namespace Isolation**
   ```yaml
   job_variables:
     namespace: "prefect-trading-demo"
   ```

## Troubleshooting

### Still Getting ACCESS_DENIED

1. Check IAM role trust policy includes EKS OIDC provider
2. Verify role has S3 permissions
3. Confirm service account is annotated with role ARN
4. Check pod is using the correct service account:
   ```bash
   kubectl get pod -l app=prefect-worker -o yaml | grep serviceAccountName
   ```

### Image Pull Fails

1. Verify ECR login:
   ```bash
   aws ecr get-login-password --region us-east-2
   ```

2. Check ECR permissions in IAM role

3. Recreate image pull secret if expired

### Permission Denied Writing to S3

Ensure IAM policy includes `s3:PutObject` permission for results directory.

