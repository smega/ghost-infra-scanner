from scanner.pricing import ebs_monthly_cost, EIP_MONTHLY, NAT_GATEWAY_MONTHLY


def test_ebs_monthly_cost_known_type():
    assert ebs_monthly_cost("gp3", 100) == 8.0


def test_ebs_monthly_cost_unknown_type_falls_back_to_default():
    assert ebs_monthly_cost("mystery-type", 50) == 5.0


def test_eip_monthly_is_positive():
    assert EIP_MONTHLY > 0


def test_nat_gateway_monthly_is_positive():
    assert NAT_GATEWAY_MONTHLY > 0
