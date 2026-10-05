from datetime import datetime, timezone

import boto3

from . import __version__
from .checks import ALL_CHECKS


def _get_account_id(session: boto3.Session) -> str:
    return session.client("sts").get_caller_identity()["Account"]


def _regions_to_scan(session: boto3.Session, requested: list[str] | None) -> list[str]:
    if requested:
        return requested
    ec2 = session.client("ec2", region_name="us-east-1")
    resp = ec2.describe_regions(Filters=[{"Name": "opt-in-status", "Values": ["opt-in-not-required", "opted-in"]}])
    return sorted(r["RegionName"] for r in resp["Regions"])


def run_scan(regions: list[str] | None = None, session: boto3.Session | None = None) -> dict:
    session = session or boto3.Session()
    account_id = _get_account_id(session)
    target_regions = _regions_to_scan(session, regions)

    all_findings = []
    scanned_regions = []
    errors = []

    for region in target_regions:
        try:
            ec2 = session.client("ec2", region_name=region)
            cloudwatch = session.client("cloudwatch", region_name=region)
            for check in ALL_CHECKS:
                all_findings.extend(f.to_dict() for f in check(ec2, cloudwatch, region))
            scanned_regions.append(region)
        except Exception as exc:  # noqa: BLE001 — a bad region shouldn't kill the whole scan
            errors.append({"region": region, "error": str(exc)})

    total_waste = round(sum(f["estimated_monthly_cost_usd"] for f in all_findings), 2)

    return {
        "scanner_version": __version__,
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "account_id": account_id,
        "regions_scanned": scanned_regions,
        "errors": errors,
        "total_estimated_monthly_waste_usd": total_waste,
        "finding_count": len(all_findings),
        "findings": all_findings,
    }
