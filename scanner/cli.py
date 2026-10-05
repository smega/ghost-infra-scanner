import argparse
import json
import os
import sys

from .core import run_scan
from .notify import send_slack_notification


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="ghost-infra-scanner",
        description="Find orphaned, idle AWS resources that are quietly costing you money.",
    )
    parser.add_argument(
        "--region",
        action="append",
        dest="regions",
        help="Limit the scan to this region. Repeatable. Default: all enabled regions.",
    )
    parser.add_argument(
        "--output",
        default="-",
        help="Write the JSON report here. Default: stdout ('-').",
    )
    parser.add_argument(
        "--slack-webhook-url",
        default=os.environ.get("SLACK_WEBHOOK_URL"),
        help="Post a summary to this Slack incoming webhook. Falls back to $SLACK_WEBHOOK_URL.",
    )
    parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Exit with a non-zero status if any ghost resources are found (useful for CI gating).",
    )
    args = parser.parse_args(argv)

    report = run_scan(regions=args.regions)
    report_json = json.dumps(report, indent=2)

    if args.output == "-":
        print(report_json)
    else:
        with open(args.output, "w") as f:
            f.write(report_json)

    if args.slack_webhook_url:
        send_slack_notification(args.slack_webhook_url, report)

    if args.fail_on_findings and report["finding_count"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
