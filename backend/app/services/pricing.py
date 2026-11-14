import json
import os

from app.utils.constants import REGIONS

HOURS_PER_MONTH = 730

# (instance type, family, vCPU, RAM GB, USD per hour, on-demand Linux, us-east-1)
# Sorted from smallest to largest inside each family.
EC2_CATALOG = [
    ("t3.small", "burstable", 2, 2, 0.0208),
    ("t3.medium", "burstable", 2, 4, 0.0416),
    ("t3.large", "burstable", 2, 8, 0.0832),
    ("t3.xlarge", "burstable", 4, 16, 0.1664),
    ("t3.2xlarge", "burstable", 8, 32, 0.3328),
    ("m5.large", "general", 2, 8, 0.096),
    ("m5.xlarge", "general", 4, 16, 0.192),
    ("m5.2xlarge", "general", 8, 32, 0.384),
    ("m5.4xlarge", "general", 16, 64, 0.768),
    ("m5.8xlarge", "general", 32, 128, 1.536),
    ("m5.16xlarge", "general", 64, 256, 3.072),
    ("c5.large", "compute", 2, 4, 0.085),
    ("c5.xlarge", "compute", 4, 8, 0.17),
    ("c5.2xlarge", "compute", 8, 16, 0.34),
    ("c5.4xlarge", "compute", 16, 32, 0.68),
    ("c5.9xlarge", "compute", 36, 72, 1.53),
    ("c5.18xlarge", "compute", 72, 144, 3.06),
    ("r5.large", "memory", 2, 16, 0.126),
    ("r5.xlarge", "memory", 4, 32, 0.252),
    ("r5.2xlarge", "memory", 8, 64, 0.504),
    ("r5.4xlarge", "memory", 16, 128, 1.008),
    ("r5.8xlarge", "memory", 32, 256, 2.016),
    ("r5.16xlarge", "memory", 64, 512, 4.032),
    ("g4dn.xlarge", "gpu", 4, 16, 0.526),
    ("g4dn.2xlarge", "gpu", 8, 32, 0.752),
    ("g4dn.4xlarge", "gpu", 16, 64, 1.204),
    ("g4dn.8xlarge", "gpu", 32, 128, 2.176),
    ("g4dn.12xlarge", "gpu", 48, 192, 3.912),
]

# (instance class, vCPU, RAM GB, USD per hour, Single-AZ MySQL/PostgreSQL, us-east-1)
RDS_CATALOG = [
    ("db.t3.small", 2, 2, 0.034),
    ("db.t3.medium", 2, 4, 0.068),
    ("db.t3.large", 2, 8, 0.136),
    ("db.m5.large", 2, 8, 0.171),
    ("db.m5.xlarge", 4, 16, 0.342),
    ("db.m5.2xlarge", 8, 32, 0.684),
    ("db.r5.large", 2, 16, 0.240),
    ("db.r5.xlarge", 4, 32, 0.480),
    ("db.r5.2xlarge", 8, 64, 0.960),
    ("db.r5.4xlarge", 16, 128, 1.920),
]

# APPROXIMATE price level versus us-east-1 (assumption; live mode gives exact EC2 prices).
REGION_FACTOR = {
    "us-east-1": 1.00,
    "us-east-2": 1.00,
    "us-west-2": 1.00,
    "us-west-1": 1.17,
    "eu-west-1": 1.11,
    "eu-west-2": 1.16,
    "eu-central-1": 1.20,
    "ap-south-1": 1.05,
    "ap-south-2": 1.06,
    "ap-southeast-1": 1.25,
    "ap-southeast-2": 1.25,
    "ap-northeast-1": 1.29,
}

EBS_GP3_PER_GB = 0.08
S3_STANDARD_PER_GB = 0.023
RDS_GP3_PER_GB = 0.115
ALB_PER_HOUR = 0.0225
LCU_PER_HOUR = 0.008
LAMBDA_PER_MILLION_REQ = 0.20
LAMBDA_PER_GB_SECOND = 0.0000166667
HTTP_API_PER_MILLION = 1.00

LOCATION = {r["code"]: r["name"] for r in REGIONS}
_live_cache = {}


def factor(region):
    return REGION_FACTOR.get(region, 1.0)


def _live_ec2(instance_type, region):
    key = (instance_type, region)
    if key in _live_cache:
        return _live_cache[key]
    import boto3  # imported only in live mode

    client = boto3.client("pricing", region_name="us-east-1")
    filters = [
        ("instanceType", instance_type),
        ("location", LOCATION[region]),
        ("operatingSystem", "Linux"),
        ("tenancy", "Shared"),
        ("preInstalledSw", "NA"),
        ("capacitystatus", "Used"),
    ]
    resp = client.get_products(
        ServiceCode="AmazonEC2",
        Filters=[{"Type": "TERM_MATCH", "Field": f, "Value": v} for f, v in filters],
        MaxResults=10,
    )
    for item in resp["PriceList"]:
        data = json.loads(item)
        for term in data["terms"]["OnDemand"].values():
            for dim in term["priceDimensions"].values():
                usd = float(dim["pricePerUnit"]["USD"])
                if usd > 0:
                    _live_cache[key] = usd
                    return usd
    raise LookupError("No price returned for " + instance_type)


def ec2_hourly(instance_type, base_price, region):
    """Return (USD per hour, source) where source is 'live' or 'reference'."""
    if os.getenv("PRICING_MODE", "reference").lower() == "live":
        try:
            return _live_ec2(instance_type, region), "live"
        except Exception:
            pass
    return base_price * factor(region), "reference"


def ebs_monthly(gb, region):
    return gb * EBS_GP3_PER_GB * factor(region)


def s3_monthly(gb, region):
    return gb * S3_STANDARD_PER_GB * factor(region)


def rds_monthly(hourly, storage_gb, multi_az, region):
    mult = 2 if multi_az else 1
    return (hourly * HOURS_PER_MONTH + storage_gb * RDS_GP3_PER_GB) * mult * factor(region)


def alb_monthly(region):
    return HOURS_PER_MONTH * (ALB_PER_HOUR + LCU_PER_HOUR) * factor(region)


def transfer_monthly(gb, region):
    """Internet data transfer out: first 100 GB/month free, then tiered."""
    remaining = max(0.0, gb - 100)
    cost = 0.0
    for size, price in [(10_240, 0.09), (40_960, 0.085), (102_400, 0.07), (float("inf"), 0.05)]:
        part = min(remaining, size)
        cost += part * price
        remaining -= part
        if remaining <= 0:
            break
    return cost * factor(region)


def cloudwatch_monthly(instances):
    # per instance: 5 custom metrics ($0.30) + 3 alarms ($0.10); plus 5 GB of logs ($0.50/GB)
    return instances * (5 * 0.30 + 3 * 0.10) + 5 * 0.50


def serverless_monthly(users, region):
    requests = users * 30 * 30  # assumption: 30 requests per user per day
    gb_seconds = requests * 0.2 * 0.5  # assumption: 200 ms at 512 MB
    lam = max(0.0, requests - 1_000_000) / 1_000_000 * LAMBDA_PER_MILLION_REQ
    lam += max(0.0, gb_seconds - 400_000) * LAMBDA_PER_GB_SECOND
    api = requests / 1_000_000 * HTTP_API_PER_MILLION
    return (lam + api) * factor(region), requests
