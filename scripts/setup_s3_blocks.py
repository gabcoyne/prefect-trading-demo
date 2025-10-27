"""
Setup Prefect S3 blocks for result storage.
Run this once to configure S3 storage for Prefect results.
"""

from prefect_aws import S3Bucket, AwsCredentials


def create_s3_blocks():
    """Create S3 bucket block and storage for Prefect."""

    # Create AWS credentials block (if needed)
    # Note: If using instance profile or environment variables, this may not be needed
    print("Setting up S3 blocks...")

    # Create S3 bucket block for results storage
    s3_bucket = S3Bucket(
        bucket_name="se-demo-raw-data-files",
        bucket_folder="prefect_results",
    )

    # Save the block
    block_name = "trading-demo-results"
    s3_bucket.save(block_name, overwrite=True)

    print(f"✓ Created S3 bucket block: {block_name}")
    print(f"  - Bucket: se-demo-raw-data-files")
    print(f"  - Folder: prefect_results")
    print()
    print("You can now use this block in your flows with:")
    print(f'  s3_bucket = S3Bucket.load("{block_name}")')


if __name__ == "__main__":
    create_s3_blocks()
