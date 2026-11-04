import boto3
from moto import mock_aws

from scanner.checks.snapshot import check_orphaned_snapshots


@mock_aws
def test_flags_snapshot_of_deleted_volume_only():
    region = "us-east-1"
    ec2 = boto3.client("ec2", region_name=region)
    az = f"{region}a"

    # Volume still exists, should NOT be flagged.
    kept = ec2.create_volume(Size=10, AvailabilityZone=az)
    ec2.create_snapshot(VolumeId=kept["VolumeId"])

    # Volume deleted, nothing uses the snapshot, should be flagged.
    gone = ec2.create_volume(Size=40, AvailabilityZone=az)
    orphan = ec2.create_snapshot(VolumeId=gone["VolumeId"])
    ec2.delete_volume(VolumeId=gone["VolumeId"])

    # A snapshot backing one of our AMIs, should NOT be flagged.
    # (moto attaches its own snapshot to registered images, so read it back.)
    image_id = ec2.register_image(Name="still-needed", RootDeviceName="/dev/xvda")["ImageId"]
    image = ec2.describe_images(ImageIds=[image_id])["Images"][0]
    backing = image["BlockDeviceMappings"][0]["Ebs"]["SnapshotId"]

    findings = check_orphaned_snapshots(ec2, cloudwatch_client=None, region=region)
    ids = {f.resource_id for f in findings}

    assert orphan["SnapshotId"] in ids
    assert backing not in ids
    assert not any(f.metadata["source_volume_id"] == kept["VolumeId"] for f in findings)
    flagged = next(f for f in findings if f.resource_id == orphan["SnapshotId"])
    assert flagged.estimated_monthly_cost_usd == 2.0  # 40 GB * $0.05/GB
