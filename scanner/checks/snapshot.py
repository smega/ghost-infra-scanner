"""EBS snapshots whose source volume is gone and that no AMI of ours uses:
leftovers from deleted volumes, old backups, copies nobody needs."""
from ..models import Finding
from ..pricing import snapshot_monthly_cost
from ._ec2_usage import existing_volume_ids, image_snapshot_ids, own_images


def check_orphaned_snapshots(ec2_client, cloudwatch_client, region: str) -> list[Finding]:
    volumes = existing_volume_ids(ec2_client)
    used_by_images = {sid for image in own_images(ec2_client) for sid in image_snapshot_ids(image)}

    findings = []
    for page in ec2_client.get_paginator("describe_snapshots").paginate(OwnerIds=["self"]):
        for snap in page["Snapshots"]:
            snapshot_id = snap["SnapshotId"]
            volume_id = snap.get("VolumeId")
            if volume_id in volumes or snapshot_id in used_by_images:
                continue

            size_gb = snap["VolumeSize"]
            tier = snap.get("StorageTier", "standard")
            name_tag = next((t["Value"] for t in snap.get("Tags", []) if t["Key"] == "Name"), None)

            findings.append(
                Finding(
                    resource_type="ebs_snapshot",
                    resource_id=snapshot_id,
                    region=region,
                    reason=f"Snapshot of {volume_id or 'an unknown volume'} ({size_gb} GB): the volume no longer exists and no AMI uses it.",
                    estimated_monthly_cost_usd=snapshot_monthly_cost(size_gb, tier),
                    metadata={
                        "size_gb": size_gb,
                        "source_volume_id": volume_id,
                        "storage_tier": tier,
                        "name_tag": name_tag,
                        "description": snap.get("Description", ""),
                        "start_time": snap["StartTime"].isoformat(),
                    },
                    console_url=f"https://{region}.console.aws.amazon.com/ec2/home?region={region}#SnapshotDetails:snapshotId={snapshot_id}",
                )
            )
    return findings
