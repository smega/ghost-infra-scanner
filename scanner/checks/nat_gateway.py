"""
NAT Gateways that have moved essentially zero traffic in the lookback window.

A NAT Gateway bills a flat hourly rate regardless of traffic, so one left
behind after a test environment is torn down (but the gateway wasn't) quietly
burns money 24/7. We flag gateways whose total bytes processed over the
lookback period falls under a small threshold — not zero, to tolerate
background chatter (health checks, DNS, etc.) without false-negatives on
truly idle gateways.
"""
from datetime import datetime, timedelta, timezone

from ..models import Finding
from ..pricing import NAT_GATEWAY_MONTHLY

LOOKBACK_DAYS = 7
IDLE_THRESHOLD_BYTES = 5 * 1024 * 1024  # 5 MB total over the lookback window


def _sum_metric(cloudwatch_client, nat_gateway_id: str, metric_name: str, start, end) -> float:
    resp = cloudwatch_client.get_metric_statistics(
        Namespace="AWS/NATGateway",
        MetricName=metric_name,
        Dimensions=[{"Name": "NatGatewayId", "Value": nat_gateway_id}],
        StartTime=start,
        EndTime=end,
        Period=86400,
        Statistics=["Sum"],
    )
    return sum(point["Sum"] for point in resp.get("Datapoints", []))


def check_idle_nat_gateways(ec2_client, cloudwatch_client, region: str) -> list[Finding]:
    findings = []
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=LOOKBACK_DAYS)

    paginator = ec2_client.get_paginator("describe_nat_gateways")
    for page in paginator.paginate(Filter=[{"Name": "state", "Values": ["available"]}]):
        for gw in page["NatGateways"]:
            nat_id = gw["NatGatewayId"]

            bytes_out = _sum_metric(cloudwatch_client, nat_id, "BytesOutToDestination", start, end)
            bytes_in = _sum_metric(cloudwatch_client, nat_id, "BytesInFromDestination", start, end)
            total_bytes = bytes_out + bytes_in

            if total_bytes > IDLE_THRESHOLD_BYTES:
                continue  # actually carrying traffic

            name_tag = next((t["Value"] for t in gw.get("Tags", []) if t["Key"] == "Name"), None)

            findings.append(
                Finding(
                    resource_type="nat_gateway",
                    resource_id=nat_id,
                    region=region,
                    reason=(
                        f"NAT Gateway moved only {total_bytes / 1024:.1f} KB in the last "
                        f"{LOOKBACK_DAYS} days — likely left behind after a teardown."
                    ),
                    estimated_monthly_cost_usd=NAT_GATEWAY_MONTHLY,
                    metadata={
                        "vpc_id": gw.get("VpcId"),
                        "subnet_id": gw.get("SubnetId"),
                        "name_tag": name_tag,
                        "lookback_days": LOOKBACK_DAYS,
                        "total_bytes_in_window": total_bytes,
                    },
                    console_url=f"https://{region}.console.aws.amazon.com/vpcconsole/home?region={region}#NatGatewayDetails:natGatewayId={nat_id}",
                )
            )
    return findings
