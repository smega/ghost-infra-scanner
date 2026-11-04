"""AMIs we own that no instance runs and no launch template points at.
Their backing snapshots keep billing until the AMI is deregistered."""
from datetime import datetime, timedelta, timezone

from ..models import Finding
from ..pricing import snapshot_monthly_cost
from ._ec2_usage import image_ids_in_use, image_snapshot_ids, own_images

# Freshly baked images are often not in use yet, give them some time.
MIN_AGE_DAYS = 30


def check_unused_amis(ec2_client, cloudwatch_client, region: str) -> list[Finding]:
    in_use = image_ids_in_use(ec2_client)
    cutoff = datetime.now(timezone.utc) - timedelta(days=MIN_AGE_DAYS)

    findings = []
    for image in own_images(ec2_client):
        image_id = image["ImageId"]
        created = datetime.fromisoformat(image["CreationDate"].replace("Z", "+00:00"))
        if image_id in in_use or created > cutoff:
            continue

        size_gb = sum(
            bdm["Ebs"].get("VolumeSize", 0) for bdm in image.get("BlockDeviceMappings", []) if bdm.get("Ebs")
        )
        age_days = (datetime.now(timezone.utc) - created).days

        findings.append(
            Finding(
                resource_type="ami",
                resource_id=image_id,
                region=region,
                reason=f"AMI {image.get('Name') or image_id} is {age_days} days old and no instance or launch template uses it.",
                estimated_monthly_cost_usd=snapshot_monthly_cost(size_gb),
                metadata={
                    "name": image.get("Name"),
                    "size_gb": size_gb,
                    "snapshot_ids": image_snapshot_ids(image),
                    "creation_date": image["CreationDate"],
                    "age_days": age_days,
                },
                console_url=f"https://{region}.console.aws.amazon.com/ec2/home?region={region}#ImageDetails:imageId={image_id}",
            )
        )
    return findings
