"""
Create ECR repository for the trading partition demo.
Run this once before deploying.
"""

import boto3
import sys


def create_ecr_repository(
    repository_name: str = "se-demos/trading-partition-demo", region: str = "us-east-2"
):
    """
    Create an ECR repository if it doesn't already exist.

    Args:
        repository_name: Name of the ECR repository
        region: AWS region
    """
    ecr_client = boto3.client("ecr", region_name=region)

    try:
        # Check if repository exists
        response = ecr_client.describe_repositories(repositoryNames=[repository_name])
        print(f"✓ ECR repository already exists: {repository_name}")
        repo_uri = response["repositories"][0]["repositoryUri"]
        print(f"  URI: {repo_uri}")
        return repo_uri

    except ecr_client.exceptions.RepositoryNotFoundException:
        # Repository doesn't exist, create it
        print(f"Creating ECR repository: {repository_name}")

        try:
            response = ecr_client.create_repository(
                repositoryName=repository_name,
                imageScanningConfiguration={"scanOnPush": True},
                imageTagMutability="MUTABLE",
            )

            repo_uri = response["repository"]["repositoryUri"]
            print(f"✓ Successfully created ECR repository")
            print(f"  Name: {repository_name}")
            print(f"  URI: {repo_uri}")
            print(f"  Region: {region}")

            return repo_uri

        except Exception as e:
            print(f"Error creating repository: {e}")
            sys.exit(1)

    except Exception as e:
        print(f"Error checking repository: {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_ecr_repository()
