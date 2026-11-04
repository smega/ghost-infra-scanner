from .ami import check_unused_amis
from .ebs import check_unattached_volumes
from .eip import check_unassociated_addresses
from .nat_gateway import check_idle_nat_gateways
from .snapshot import check_orphaned_snapshots

ALL_CHECKS = [
    check_unattached_volumes,
    check_unassociated_addresses,
    check_idle_nat_gateways,
    check_orphaned_snapshots,
    check_unused_amis,
]
