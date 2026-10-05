"""Unattached (status=available) EBS volumes: allocated, billed, doing nothing."""
from ..models import Finding
from ..pricing import ebs_monthly_cost


def check_unattached_volumes(ec2_client, cloudwatch_client, region: str) -> list[Finding]:
    findings = []
    paginator = ec2_client.get_paginator("describe_volumes")
    for page in paginator.paginate(Filters=[{"Name": "status", "Values": ["available"]}]):
        for vol in page["Volumes"]:
            volume_id = vol["VolumeId"]
            size_gb = vol["Size"]
            volume_type = vol.get("VolumeType", "gp2")
            cost = ebs_monthly_cost(volume_type, size_gb)
            name_tag = next((t["Value"] for t in vol.get("Tags", []) if t["Key"] == "Name"), None)

            findings.append(
                Finding(
                    resource_type="ebs_volume",
                    resource_id=volume_id,
                    region=region,
                    reason=f"Unattached {volume_type} volume ({size_gb} GB), not connected to any instance.",
                    estimated_monthly_cost_usd=cost,
                    metadata={
                        "size_gb": size_gb,
                        "volume_type": volume_type,
                        "name_tag": name_tag,
                        "create_time": vol["CreateTime"].isoformat(),
                    },
                    console_url=f"https://{region}.console.aws.amazon.com/ec2/home?region={region}#VolumeDetails:volumeId={volume_id}",
                )
            )
    return findings
