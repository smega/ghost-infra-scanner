"""
Rough, static USD cost estimates for common AWS resources.

These are NOT pulled from the AWS Price List API or Cost Explorer. They are
conservative on-demand us-east-1 list prices, hardcoded, so the scanner only
ever needs read-only Describe/Get permissions (no ce:* / pricing:* access).
Treat every number here as "ballpark", not an invoice.
"""

HOURS_PER_MONTH = 730

# EBS volume type -> USD per GB-month (us-east-1, on-demand, Oct 2026 list price)
EBS_GB_MONTH = {
    "gp3": 0.08,
    "gp2": 0.10,
    "io1": 0.125,
    "io2": 0.125,
    "st1": 0.045,
    "sc1": 0.015,
    "standard": 0.05,
}
EBS_GB_MONTH_DEFAULT = 0.10

# Elastic IP: AWS started charging for ALL public IPv4 addresses in 2024,
# whether attached or not. An idle/unassociated EIP carries the same base
# hourly charge as an attached one. The "waste" here is that it's allocated
# and doing nothing, not that it's specifically more expensive while idle.
EIP_HOURLY = 0.005
EIP_MONTHLY = round(EIP_HOURLY * HOURS_PER_MONTH, 2)  # ~3.65 USD/month

# NAT Gateway: flat hourly charge regardless of traffic, plus per-GB
# data processing. An idle gateway still burns the full hourly charge.
NAT_GATEWAY_HOURLY = 0.045
NAT_GATEWAY_MONTHLY = round(NAT_GATEWAY_HOURLY * HOURS_PER_MONTH, 2)  # ~32.85 USD/month


def ebs_monthly_cost(volume_type: str, size_gb: int) -> float:
    rate = EBS_GB_MONTH.get(volume_type, EBS_GB_MONTH_DEFAULT)
    return round(rate * size_gb, 2)
