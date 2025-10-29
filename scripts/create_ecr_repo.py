"""Create ECR repository for Docker images."""

import boto3
import sys


REPO_NAME = "se-demos/trading-partition-demo"
REGION = "us-east-2"


def create_repository():
    """Create ECR repository if it doesn't exist."""
    ecr = boto3.client("ecr", region_name=REGION)
    
    try:
        response = ecr.describe_repositories(repositoryNames=[REPO_NAME])
        repo_uri = response["repositories"][0]["repositoryUri"]
        print(f"Repository exists: {repo_uri}")
        return repo_uri
    except ecr.exceptions.RepositoryNotFoundException:
        pass
    
    try:
        response = ecr.create_repository(
            repositoryName=REPO_NAME,
            imageScanningConfiguration={"scanOnPush": True},
            imageTagMutability="MUTABLE",
        )
        repo_uri = response["repository"]["repositoryUri"]
        print(f"Created repository: {repo_uri}")
        return repo_uri
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_repository()
