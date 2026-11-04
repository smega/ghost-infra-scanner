import boto3
from moto import mock_aws

from scanner.checks import ami as ami_check


def _register(ec2, name):
    return ec2.register_image(Name=name, RootDeviceName="/dev/xvda")["ImageId"]


@mock_aws
def test_flags_ami_no_instance_or_launch_template_uses(monkeypatch):
    # moto creates every image "now", so drop the minimum age for the test
    monkeypatch.setattr(ami_check, "MIN_AGE_DAYS", -1)
    region = "us-east-1"
    ec2 = boto3.client("ec2", region_name=region)

    running = _register(ec2, "running")
    ec2.run_instances(ImageId=running, MinCount=1, MaxCount=1)

    templated = _register(ec2, "templated")
    ec2.create_launch_template(LaunchTemplateName="web", LaunchTemplateData={"ImageId": templated})

    unused = _register(ec2, "unused")

    findings = ami_check.check_unused_amis(ec2, cloudwatch_client=None, region=region)

    flagged = {f.resource_id for f in findings}

    assert unused in flagged
    assert running not in flagged
    assert templated not in flagged
    unused_finding = next(f for f in findings if f.resource_id == unused)
    assert unused_finding.estimated_monthly_cost_usd == round(unused_finding.metadata["size_gb"] * 0.05, 2)


@mock_aws
def test_skips_recent_amis():
    region = "us-east-1"
    ec2 = boto3.client("ec2", region_name=region)
    fresh = _register(ec2, "fresh")

    findings = ami_check.check_unused_amis(ec2, cloudwatch_client=None, region=region)
    assert fresh not in {f.resource_id for f in findings}
