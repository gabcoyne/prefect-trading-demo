"""Create Prefect S3 blocks for input data and results storage."""

from prefect_aws import S3Bucket

BUCKET = "se-demo-raw-data-files"

def create_s3_blocks():
    """
    Create S3 blocks for the trading demo:
    - trading-demo-input: For raw data files (spx_holdings, vix, spx)
    - trading-demo-results: For analysis output files
    """
    
    # Note: AWS credentials are picked up from environment or AWS config
    # No need to explicitly create AwsCredentials block if using default credentials
    
    # Block 1: Input data storage
    input_bucket = S3Bucket(
        bucket_name=BUCKET,
        bucket_folder="",  # Root of bucket for input files
    )
    input_bucket.save(name="trading-demo-input", overwrite=True)
    print("✓ Created S3 block: trading-demo-input")
    print(f"  → s3://{BUCKET}/")
    
    # Block 2: Results storage
    results_bucket = S3Bucket(
        bucket_name=BUCKET,
        bucket_folder="trading-results",  # Subfolder for results
    )
    results_bucket.save(name="trading-demo-results", overwrite=True)
    print("✓ Created S3 block: trading-demo-results")
    print(f"  → s3://{BUCKET}/trading-results/")
    
    # Reference
    print("\nS3 blocks created successfully!")
    print("\nUsage in flows:")
    print("  from prefect_aws import S3Bucket")
    print("  s3_block = await S3Bucket.load('trading-demo-input')")
    print("  df = pd.read_parquet(s3_block.get_directory())")


if __name__ == "__main__":
    create_s3_blocks()

