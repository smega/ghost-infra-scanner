"""Elastic IPs allocated but not associated with a running instance/ENI."""
from ..models import Finding
from ..pricing import EIP_MONTHLY


def check_unassociated_addresses(ec2_client, cloudwatch_client, region: str) -> list[Finding]:
    findings = []
    response = ec2_client.describe_addresses()
    for addr in response["Addresses"]:
        if addr.get("AssociationId"):
            continue  # in use, skip

        allocation_id = addr.get("AllocationId", addr["PublicIp"])
        name_tag = next((t["Value"] for t in addr.get("Tags", []) if t["Key"] == "Name"), None)

        findings.append(
            Finding(
                resource_type="elastic_ip",
                resource_id=allocation_id,
                region=region,
                reason=f"Elastic IP {addr['PublicIp']} is allocated but not attached to anything.",
                estimated_monthly_cost_usd=EIP_MONTHLY,
                metadata={
                    "public_ip": addr["PublicIp"],
                    "name_tag": name_tag,
                },
                console_url=f"https://{region}.console.aws.amazon.com/ec2/home?region={region}#Addresses:",
            )
        )
    return findings
