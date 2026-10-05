import boto3
from moto import mock_aws

from scanner.checks.ebs import check_unattached_volumes


@mock_aws
def test_flags_unattached_volume_but_not_attached_one():
    region = "us-east-1"
    ec2 = boto3.client("ec2", region_name=region)

    # An unattached volume, should be flagged.
    ec2.create_volume(Size=20, AvailabilityZone=f"{region}a", VolumeType="gp3")

    # An attached volume, should NOT be flagged.
    attached = ec2.create_volume(Size=10, AvailabilityZone=f"{region}a", VolumeType="gp3")
    reservation = ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1)
    instance_id = reservation["Instances"][0]["InstanceId"]
    ec2.attach_volume(VolumeId=attached["VolumeId"], InstanceId=instance_id, Device="/dev/sdf")

    findings = check_unattached_volumes(ec2, cloudwatch_client=None, region=region)

    assert len(findings) == 1
    assert findings[0].metadata["size_gb"] == 20
    assert findings[0].estimated_monthly_cost_usd == 1.6  # 20 GB * $0.08/GB
