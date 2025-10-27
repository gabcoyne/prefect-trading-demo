"""
Helper script to upload parquet data files to S3.
Run this before deploying to ensure all data files are available in S3.
"""

import boto3
import sys
from pathlib import Path


def upload_to_s3(
    local_file: str, bucket: str = "se-demo-raw-data-files", s3_key: str = None
):
    """
    Upload a local parquet file to S3.

    Args:
        local_file: Local path to the parquet file
        bucket: S3 bucket name
        s3_key: S3 object key (path in bucket), defaults to filename
    """
    # Check if file exists
    if not Path(local_file).exists():
        print(f"⚠️  File {local_file} not found, skipping...")
        return False

    # Use filename as S3 key if not specified
    if s3_key is None:
        s3_key = Path(local_file).name

    # Get file size
    file_size = Path(local_file).stat().st_size
    file_size_mb = file_size / (1024 * 1024)

    print(f"Uploading {local_file} to s3://{bucket}/{s3_key}")
    print(f"  File size: {file_size_mb:.2f} MB")

    # Upload to S3
    s3_client = boto3.client("s3")

    try:
        s3_client.upload_file(
            local_file,
            bucket,
            s3_key,
            ExtraArgs={"ContentType": "application/octet-stream"},
        )
        print(f"  ✓ Successfully uploaded to s3://{bucket}/{s3_key}")
        return True
    except Exception as e:
        print(f"  ❌ Error uploading file: {e}")
        return False


def upload_all_data_files():
    """Upload all required data files to S3."""
    bucket = "se-demo-raw-data-files"

    files_to_upload = [
        "spx_holdings_hourly.parquet",  # Stock prices
        "vix_hourly.parquet",  # Volatility index
        "spx_hourly.parquet",  # S&P 500 index
    ]

    print("=" * 60)
    print("Uploading Trading Data Files to S3")
    print("=" * 60)
    print(f"Target bucket: s3://{bucket}/")
    print()

    success_count = 0
    for filename in files_to_upload:
        if upload_to_s3(filename, bucket, filename):
            success_count += 1
        print()

    print("=" * 60)
    print(f"Upload complete: {success_count}/{len(files_to_upload)} files uploaded")
    print("=" * 60)

    if success_count < len(files_to_upload):
        print("\n⚠️  Some files were not uploaded. Generate missing files with:")
        print("    cd input && python generate_hourly_data.py")
        sys.exit(1)


if __name__ == "__main__":
    upload_all_data_files()
