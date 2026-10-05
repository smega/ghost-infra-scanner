import json
import urllib.request

MAX_ITEMS_IN_MESSAGE = 10

_LABELS = {
    "ebs_volume": "Unattached EBS volume",
    "elastic_ip": "Unassociated Elastic IP",
    "nat_gateway": "Idle NAT Gateway",
}


def _format_slack_payload(report: dict) -> dict:
    findings = report["findings"]
    total = report["total_estimated_monthly_waste_usd"]
    account_id = report["account_id"]

    if not findings:
        text = f"✅ *Ghost Infrastructure scan* for `{account_id}` — nothing found. Clean account."
        return {"text": text}

    lines = [
        f"👻 *Ghost Infrastructure Report* — account `{account_id}`",
        f"Found *{len(findings)}* idle resource(s), estimated *${total}/month* wasted.",
        "",
    ]

    sorted_findings = sorted(findings, key=lambda f: f["estimated_monthly_cost_usd"], reverse=True)
    for f in sorted_findings[:MAX_ITEMS_IN_MESSAGE]:
        label = _LABELS.get(f["resource_type"], f["resource_type"])
        lines.append(
            f"• *{label}* `{f['resource_id']}` ({f['region']}) — "
            f"${f['estimated_monthly_cost_usd']}/mo. {f['reason']}"
            + (f" <{f['console_url']}|Open in console>" if f.get("console_url") else "")
        )

    remaining = len(sorted_findings) - MAX_ITEMS_IN_MESSAGE
    if remaining > 0:
        lines.append(f"_…and {remaining} more. See the full JSON artifact for the complete list._")

    return {"text": "\n".join(lines)}


def send_slack_notification(webhook_url: str, report: dict) -> None:
    payload = _format_slack_payload(report)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.status >= 300:
            raise RuntimeError(f"Slack webhook returned HTTP {resp.status}")
