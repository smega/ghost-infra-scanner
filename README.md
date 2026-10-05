# ghost-infra-scanner

Finds AWS resources that are allocated, billed, and doing absolutely nothing:
the unattached EBS volume from a test that never got cleaned up, the Elastic
IP nobody released, the NAT Gateway still running after the environment it
served was torn down. Posts a plain-language summary to Slack so you find out
before the invoice does.

No dashboard to log into, no agent to install, no standing access to your
AWS account. It's a script you can read top to bottom in five minutes, run on
a schedule via GitHub Actions, and point at your own Slack webhook.

## Why this exists

> "We found a stray NAT Gateway leaking $600/month."

That sentence shows up constantly on r/aws and r/devops. Native AWS tooling
either doesn't catch it (Cost Explorer tells you spend went up, not which
specific resource) or sits behind a paid Business/Enterprise Support plan
(Trusted Advisor's cost checks). The well-funded FinOps platforms (Vantage,
CloudZero, Zesty, …) are built, and priced, for companies spending tens of
thousands a month, not a five-person startup's $400 bill.

This tool checks for exactly three things, does it well, and gets out of
your way.

## What it checks

| Check | What it flags |
|---|---|
| Unattached EBS volumes | Volumes in `available` state, not attached to any instance |
| Unassociated Elastic IPs | Allocated IPs with no `AssociationId` |
| Idle NAT Gateways | Gateways moving under 5 MB of traffic over the last 7 days |

Cost estimates are static, conservative, on-demand list prices (see
[`scanner/pricing.py`](scanner/pricing.py)), not pulled from the Cost
Explorer or Price List APIs, deliberately, so the scanner never needs
billing-related permissions. Treat the dollar figures as "ballpark," not an
invoice line item.

More checks (idle load balancers, orphaned snapshots, unused RDS instances)
are natural next additions, see [Roadmap](#roadmap).

## Security model

This is the part that usually matters more than the feature list:

- **No standing access.** The scanner authenticates via [GitHub Actions OIDC](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect): AWS issues short-lived, scoped credentials for the duration of a single workflow run. Nothing is stored, by you, by us (there is no "us" with access, this is just a script), or by GitHub beyond the run itself.
- **Read-only, enumerated permissions.** The IAM policy the scanner needs is six `Describe`/`Get` actions, nothing else. See [`iam/scan-policy.json`](iam/scan-policy.json), it's short enough to read in full before you attach it.
- **Nothing leaves your infrastructure except what you choose to send.** The scan runs inside your own GitHub Actions runner, using your own AWS role, and posts to a Slack webhook URL *you* control. There's no third-party backend in this loop at all.
- **It's ~250 lines of Python.** Read [`scanner/checks/`](scanner/checks/) before you trust it. That's the point of it being open source rather than a SaaS you'd have to take on faith.

## Quickstart

### 1. Create the IAM role (OIDC, read-only)

Set up a GitHub OIDC identity provider in your AWS account (one-time, [AWS docs here](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)), then create a role using:

- Trust policy: [`iam/trust-policy.json`](iam/trust-policy.json) (fill in your account ID, org, and repo)
- Permissions policy: [`iam/scan-policy.json`](iam/scan-policy.json) (use as-is)

### 2. Add two repo secrets

In your fork/repo's Settings → Secrets and variables → Actions:

- `AWS_SCAN_ROLE_ARN`: the role ARN from step 1
- `SLACK_WEBHOOK_URL`: an [incoming webhook URL](https://api.slack.com/messaging/webhooks) for the channel you want alerts in

### 3. Enable the workflow

[`.github/workflows/scan.yml`](.github/workflows/scan.yml) is already wired up to run daily at 07:00 UTC and on manual dispatch. Adjust the cron, commit, done.

### Running it locally (no GitHub Action needed)

```bash
pip install .
export AWS_PROFILE=your-profile   # any credentials with the policy above
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
ghost-infra-scanner --output report.json
```

Omit `--slack-webhook-url`/`$SLACK_WEBHOOK_URL` to just get the JSON on stdout, useful for piping into `jq` or your own tooling.

## Example output

```json
{
  "account_id": "123456789012",
  "total_estimated_monthly_waste_usd": 40.85,
  "finding_count": 2,
  "findings": [
    {
      "resource_type": "nat_gateway",
      "resource_id": "nat-0abc123def456",
      "reason": "NAT Gateway moved only 0.0 KB in the last 7 days, likely left behind after a teardown.",
      "estimated_monthly_cost_usd": 32.85
    },
    {
      "resource_type": "ebs_volume",
      "resource_id": "vol-0123456789abcdef0",
      "reason": "Unattached gp3 volume (100 GB), not connected to any instance.",
      "estimated_monthly_cost_usd": 8.0
    }
  ]
}
```

Slack gets a condensed, human-readable version of the same thing.

## Roadmap

- [ ] Idle Application/Classic Load Balancers (zero healthy targets or zero requests)
- [ ] Orphaned EBS snapshots (source volume no longer exists)
- [ ] Unused RDS instances (no connections in N days)
- [ ] GCP equivalent checks

## Contributing

Issues and PRs welcome, especially new checks. Each check is a single function with the signature `(ec2_client, cloudwatch_client, region) -> list[Finding]`; see [`scanner/checks/ebs.py`](scanner/checks/ebs.py) for the shortest example to copy from.

```bash
pip install -e . -r requirements-dev.txt
pytest
```

## License

MIT, see [`LICENSE`](LICENSE).
