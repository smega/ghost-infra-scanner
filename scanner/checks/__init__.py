from .ebs import check_unattached_volumes
from .eip import check_unassociated_addresses
from .nat_gateway import check_idle_nat_gateways

ALL_CHECKS = [
    check_unattached_volumes,
    check_unassociated_addresses,
    check_idle_nat_gateways,
]
