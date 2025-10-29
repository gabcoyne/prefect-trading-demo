"""Upload parquet data files to S3 using Prefect S3 blocks."""

import sys
from pathlib import Path
from prefect_aws import S3Bucket


FILES = [
    "spx_holdings_hourly.parquet",
    "vix_hourly.parquet",
    "spx_hourly.parquet",
]


def upload_file(s3_block: S3Bucket, local_path: str, s3_key: str = None):
    """Upload file to S3 using Prefect S3 block."""
    path = Path(local_path)
    
    if not path.exists():
        print(f"Skipping {local_path} (not found)")
        return False
    
    if s3_key is None:
        s3_key = path.name
    
    size_mb = path.stat().st_size / (1024 * 1024)
    bucket_path = f"{s3_block.bucket_name}/{s3_block.bucket_folder}/{s3_key}".replace("//", "/")
    print(f"Uploading {local_path} ({size_mb:.1f} MB) -> s3://{bucket_path}")
    
    try:
        s3_block.upload_from_path(from_path=local_path, to_path=s3_key)
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False


def main():
    # Load S3 block
    try:
        s3_block = S3Bucket.load_sync(name="trading-demo-input")
    except ValueError:
        print("Error: S3 block 'trading-demo-input' not found.")
        print("Create it first with: python scripts/create_s3_blocks.py")
        sys.exit(1)
    
    bucket_path = f"{s3_block.bucket_name}/{s3_block.bucket_folder}".rstrip("/")
    print(f"Uploading to s3://{bucket_path}/\n")
    
    uploaded = sum(1 for f in FILES if upload_file(s3_block, f))
    
    print(f"\nComplete: {uploaded}/{len(FILES)} files uploaded")
    
    if uploaded < len(FILES):
        print("\nGenerate missing files with: cd input && python generate_hourly_data.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
