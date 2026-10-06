"""
Optional: upload a scan report to a hosted Ghost Infra backend instead of
(or alongside) a Slack webhook. Translates this scanner's finding format
into the backend's Inventory/Resource upload schema, then POSTs it to
/api/ingest with an API key, same as the Go collector does.
"""
import json
import urllib.request

_TYPE_MAP = {
    "ebs_volume": "volume",
    "elastic_ip": "ip",
    "nat_gateway": "nat-gateway",
}

# How many lookback days to report as "idle for" on a NAT gateway finding,
# falling back to the scanner's own default if the metadata is missing.
_DEFAULT_NAT_LOOKBACK_DAYS = 7


def to_inventory(report: dict) -> dict:
    resources = []
    for f in report["findings"]:
        metadata = f.get("metadata", {})
        resource_type = f["resource_type"]

        resource = {
            "id": f["resource_id"],
            "name": metadata.get("name_tag") or f["resource_id"],
            "type": _TYPE_MAP.get(resource_type, resource_type),
            "region": f["region"],
            "state": "available",
            "monthlyCost": f["estimated_monthly_cost_usd"],
            "attached": False,
            "tags": {},
        }

        if resource_type == "nat_gateway":
            resource["lastUsedDaysAgo"] = metadata.get("lookback_days", _DEFAULT_NAT_LOOKBACK_DAYS)

        resources.append(resource)

    return {
        "accountName": report["account_id"],
        "provider": "aws",
        "currency": "USD",
        "generatedAt": report["scan_time"],
        "resources": resources,
    }


def upload_to_backend(backend_url: str, token: str, report: dict) -> dict:
    inventory = to_inventory(report)
    data = json.dumps(inventory).encode("utf-8")
    req = urllib.request.Request(
        backend_url.rstrip("/") + "/api/ingest",
        data=data,
        headers={"Content-Type": "application/json", "X-Ghost-Token": token},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read()
        if resp.status >= 300:
            raise RuntimeError(f"Backend upload returned HTTP {resp.status}")
        return json.loads(body) if body else {}
