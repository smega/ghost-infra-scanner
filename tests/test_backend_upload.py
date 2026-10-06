from scanner.backend_upload import to_inventory

_SAMPLE_REPORT = {
    "account_id": "123456789012",
    "scan_time": "2026-10-06T08:00:00+00:00",
    "findings": [
        {
            "resource_type": "ebs_volume",
            "resource_id": "vol-abc",
            "region": "us-east-1",
            "reason": "Unattached gp3 volume (20 GB).",
            "estimated_monthly_cost_usd": 1.6,
            "metadata": {"size_gb": 20, "volume_type": "gp3", "name_tag": "test-vol"},
        },
        {
            "resource_type": "elastic_ip",
            "resource_id": "eipalloc-xyz",
            "region": "us-east-1",
            "reason": "Allocated but not attached.",
            "estimated_monthly_cost_usd": 3.65,
            "metadata": {"public_ip": "203.0.113.5", "name_tag": None},
        },
        {
            "resource_type": "nat_gateway",
            "resource_id": "nat-0abc123",
            "region": "us-east-1",
            "reason": "Idle for 7 days.",
            "estimated_monthly_cost_usd": 32.85,
            "metadata": {"lookback_days": 7, "name_tag": None},
        },
    ],
}


def test_maps_account_and_timestamp():
    inv = to_inventory(_SAMPLE_REPORT)
    assert inv["accountName"] == "123456789012"
    assert inv["generatedAt"] == "2026-10-06T08:00:00+00:00"
    assert inv["provider"] == "aws"


def test_maps_resource_types():
    inv = to_inventory(_SAMPLE_REPORT)
    types = {r["id"]: r["type"] for r in inv["resources"]}
    assert types["vol-abc"] == "volume"
    assert types["eipalloc-xyz"] == "ip"
    assert types["nat-0abc123"] == "nat-gateway"


def test_uses_name_tag_when_present():
    inv = to_inventory(_SAMPLE_REPORT)
    by_id = {r["id"]: r for r in inv["resources"]}
    assert by_id["vol-abc"]["name"] == "test-vol"
    assert by_id["eipalloc-xyz"]["name"] == "eipalloc-xyz"  # no name tag, falls back to id


def test_nat_gateway_gets_last_used_days_ago():
    inv = to_inventory(_SAMPLE_REPORT)
    by_id = {r["id"]: r for r in inv["resources"]}
    assert by_id["nat-0abc123"]["lastUsedDaysAgo"] == 7


def test_all_resources_marked_unattached_with_cost():
    inv = to_inventory(_SAMPLE_REPORT)
    for r in inv["resources"]:
        assert r["attached"] is False
        assert r["monthlyCost"] > 0
