"""Shared lookups for checks that need to know what is still in use."""


def existing_volume_ids(ec2_client) -> set[str]:
    ids = set()
    for page in ec2_client.get_paginator("describe_volumes").paginate():
        ids.update(v["VolumeId"] for v in page["Volumes"])
    return ids


def own_images(ec2_client) -> list[dict]:
    images = []
    for page in ec2_client.get_paginator("describe_images").paginate(Owners=["self"]):
        images.extend(page["Images"])
    return images


def image_snapshot_ids(image: dict) -> list[str]:
    return [
        bdm["Ebs"]["SnapshotId"]
        for bdm in image.get("BlockDeviceMappings", [])
        if bdm.get("Ebs", {}).get("SnapshotId")
    ]


def image_ids_in_use(ec2_client) -> set[str]:
    """AMIs referenced by any non-terminated instance or by a launch template's
    default or latest version."""
    used = set()
    for page in ec2_client.get_paginator("describe_instances").paginate(
        Filters=[{"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]}]
    ):
        for reservation in page["Reservations"]:
            used.update(i["ImageId"] for i in reservation["Instances"] if i.get("ImageId"))

    for page in ec2_client.get_paginator("describe_launch_templates").paginate():
        for lt in page["LaunchTemplates"]:
            versions = ec2_client.describe_launch_template_versions(
                LaunchTemplateId=lt["LaunchTemplateId"], Versions=["$Default", "$Latest"]
            )["LaunchTemplateVersions"]
            used.update(
                v["LaunchTemplateData"]["ImageId"] for v in versions if v.get("LaunchTemplateData", {}).get("ImageId")
            )
    return used
