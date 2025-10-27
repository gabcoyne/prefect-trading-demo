"""
Data validation flow to check data quality before processing.
Validates completeness, outliers, and market data availability.
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from prefect import flow, task
from prefect.artifacts import create_markdown_artifact, create_table_artifact


@task(log_prints=True)
def check_missing_data(parquet_path: str):
    """
    Check for missing timestamps and values across contracts.

    Args:
        parquet_path: Path to stock holdings parquet file

    Returns:
        Dictionary with missing data statistics
    """
    print(f"Checking for missing data in {parquet_path}")

    df = pd.read_parquet(parquet_path)

    # Check for missing values
    missing_by_column = df.isnull().sum()
    total_values = len(df)

    issues = []
    for col in missing_by_column.index:
        if missing_by_column[col] > 0:
            pct = (missing_by_column[col] / total_values) * 100
            issues.append(
                {
                    "Contract": col,
                    "Missing": int(missing_by_column[col]),
                    "Percent": f"{pct:.2f}%",
                }
            )

    # Check for duplicate timestamps
    if df.index.duplicated().any():
        dup_count = df.index.duplicated().sum()
        print(f"⚠️  Found {dup_count} duplicate timestamps")

    result = {
        "total_records": total_values,
        "total_contracts": len(df.columns),
        "missing_value_count": int(missing_by_column.sum()),
        "contracts_with_missing": len(issues),
        "issues": issues,
    }

    if issues:
        print(f"⚠️  Found {len(issues)} contracts with missing values")
    else:
        print("✓ No missing values detected")

    return result


@task(log_prints=True)
def check_price_outliers(parquet_path: str, std_threshold: float = 3.0):
    """
    Detect price outliers using statistical methods.

    Args:
        parquet_path: Path to stock holdings parquet file
        std_threshold: Number of standard deviations to consider outlier

    Returns:
        Dictionary with outlier statistics
    """
    print(f"Checking for price outliers in {parquet_path}")

    df = pd.read_parquet(parquet_path)

    outliers = []

    for col in df.columns:
        if col == "SPX":
            continue

        prices = df[col].dropna()
        if len(prices) < 2:
            continue

        # Calculate z-scores for price changes
        price_changes = prices.pct_change().dropna()
        if len(price_changes) == 0:
            continue

        mean_change = price_changes.mean()
        std_change = price_changes.std()

        if std_change == 0:
            continue

        z_scores = (price_changes - mean_change) / std_change
        outlier_mask = abs(z_scores) > std_threshold

        if outlier_mask.any():
            outlier_count = outlier_mask.sum()
            max_z = abs(z_scores).max()
            outliers.append(
                {
                    "Contract": col,
                    "Outliers": int(outlier_count),
                    "Max Z-Score": f"{max_z:.2f}",
                }
            )

    result = {
        "outlier_threshold": std_threshold,
        "contracts_with_outliers": len(outliers),
        "outliers": outliers,
    }

    if outliers:
        print(f"⚠️  Found {len(outliers)} contracts with outliers")
    else:
        print("✓ No significant outliers detected")

    return result


@task(log_prints=True)
def check_market_data(vix_path: str, spx_path: str):
    """
    Validate VIX and SPX market data availability.

    Args:
        vix_path: Path to VIX parquet file
        spx_path: Path to SPX parquet file

    Returns:
        Dictionary with market data statistics
    """
    print(f"Checking market data: VIX and SPX")

    issues = []

    # Check VIX
    try:
        vix_df = pd.read_parquet(vix_path)
        vix_missing = vix_df["VIX"].isnull().sum()
        vix_records = len(vix_df)

        if vix_missing > 0:
            issues.append(f"VIX has {vix_missing} missing values")

        print(
            f"✓ VIX: {vix_records} records, range {vix_df['VIX'].min():.2f}-{vix_df['VIX'].max():.2f}"
        )
    except Exception as e:
        issues.append(f"Failed to load VIX: {e}")
        vix_records = 0

    # Check SPX
    try:
        spx_df = pd.read_parquet(spx_path)
        spx_missing = spx_df["SPX"].isnull().sum()
        spx_records = len(spx_df)

        if spx_missing > 0:
            issues.append(f"SPX has {spx_missing} missing values")

        print(
            f"✓ SPX: {spx_records} records, range {spx_df['SPX'].min():.2f}-{spx_df['SPX'].max():.2f}"
        )
    except Exception as e:
        issues.append(f"Failed to load SPX: {e}")
        spx_records = 0

    result = {
        "vix_records": vix_records,
        "spx_records": spx_records,
        "issues": issues,
    }

    if issues:
        print(f"⚠️  Market data issues: {len(issues)}")
    else:
        print("✓ Market data validated successfully")

    return result


@task(log_prints=True)
def create_validation_report(missing_data: Dict, outliers: Dict, market_data: Dict):
    """
    Create comprehensive validation report as artifacts.

    Args:
        missing_data: Missing data check results
        outliers: Outlier check results
        market_data: Market data check results

    Returns:
        Overall validation status (pass/warn/fail)
    """
    # Determine overall status
    critical_issues = []
    warnings = []

    if missing_data["missing_value_count"] > 0:
        warnings.append(
            f"{missing_data['contracts_with_missing']} contracts have missing values"
        )

    if outliers["contracts_with_outliers"] > 0:
        warnings.append(
            f"{outliers['contracts_with_outliers']} contracts have price outliers"
        )

    if market_data["issues"]:
        critical_issues.extend(market_data["issues"])

    if market_data["vix_records"] == 0 or market_data["spx_records"] == 0:
        critical_issues.append("Missing required market data (VIX or SPX)")

    # Determine status
    if critical_issues:
        status = "FAIL"
        status_emoji = "❌"
    elif warnings:
        status = "WARN"
        status_emoji = "⚠️"
    else:
        status = "PASS"
        status_emoji = "✅"

    # Create summary markdown artifact
    create_markdown_artifact(
        key="validation-summary",
        markdown=f"""# Data Validation Report

## Overall Status: {status_emoji} {status}

### Stock Data
- **Total Records**: {missing_data['total_records']:,}
- **Total Contracts**: {missing_data['total_contracts']}
- **Contracts with Missing Values**: {missing_data['contracts_with_missing']}
- **Contracts with Outliers**: {outliers['contracts_with_outliers']}

### Market Data
- **VIX Records**: {market_data['vix_records']:,}
- **SPX Records**: {market_data['spx_records']:,}

### Issues
{"#### Critical Issues" if critical_issues else ""}
{chr(10).join(f"- ❌ {issue}" for issue in critical_issues)}

{"#### Warnings" if warnings else ""}
{chr(10).join(f"- ⚠️ {warning}" for warning in warnings)}

{"#### ✅ All validation checks passed!" if status == "PASS" else ""}
        """,
        description="Data validation summary",
    )

    # Create detailed tables for issues if any
    if missing_data["issues"]:
        create_table_artifact(
            key="validation-missing-data",
            table=missing_data["issues"],
            description="Contracts with missing values",
        )

    if outliers["outliers"]:
        create_table_artifact(
            key="validation-outliers",
            table=outliers["outliers"][:20],  # Limit to top 20
            description="Contracts with price outliers",
        )

    return {
        "status": status,
        "critical_issues": critical_issues,
        "warnings": warnings,
    }


@flow(
    name="validate-data",
    flow_run_name="validate-data",
    persist_result=True,
    log_prints=True,
)
def validate_data(
    parquet_path: str = "s3://se-demo-raw-data-files/spx_holdings_hourly.parquet",
    vix_path: str = "s3://se-demo-raw-data-files/vix_hourly.parquet",
    spx_path: str = "s3://se-demo-raw-data-files/spx_hourly.parquet",
):
    """
    Validate data quality before processing.

    Performs multiple validation checks:
    - Missing timestamps and values
    - Price outliers
    - Market data availability

    Args:
        parquet_path: Path to stock holdings parquet file
        vix_path: Path to VIX parquet file
        spx_path: Path to SPX parquet file

    Returns:
        Validation result with status (PASS/WARN/FAIL)
    """
    # Run validation checks
    missing_data = check_missing_data(parquet_path)
    outliers = check_price_outliers(parquet_path)
    market_data = check_market_data(vix_path, spx_path)

    # Create validation report
    result = create_validation_report(missing_data, outliers, market_data)

    print(f"\n{'='*50}")
    print(f"Validation Status: {result['status']}")
    print(f"{'='*50}")

    return result


if __name__ == "__main__":
    # Test with local paths
    result = validate_data(
        parquet_path="spx_holdings_hourly.parquet",
        vix_path="vix_hourly.parquet",
        spx_path="spx_hourly.parquet",
    )
    print(f"\nValidation result: {result}")
