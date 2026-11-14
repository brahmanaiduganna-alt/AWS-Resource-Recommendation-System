import math
from pathlib import Path

import joblib
import pandas as pd

from app.services import pricing
from app.services.features import engineer

MODELS_DIR = Path(__file__).resolve().parents[3] / "ml" / "models"
_models = {}

HA_USER_THRESHOLD = 1000
SAVINGS_PLAN_DISCOUNT = 0.28
SPOT_DISCOUNT = 0.65
S3_CATEGORIES = {"Video Streaming", "Data Analytics", "IoT"}
CDN_CATEGORIES = {"Website Hosting", "Video Streaming", "E-Commerce"}
SPOT_CATEGORIES = {"AI/ML", "DevOps", "Data Analytics"}
RDS_CATEGORIES = {"E-Commerce", "Mobile App"}
DYNAMO_CATEGORIES = {"IoT", "Serverless"}


def r2(x):
    return round(float(x), 2)


def _load():
    if not _models:
        _models["reg"] = joblib.load(MODELS_DIR / "resource_regressor.joblib")
        _models["fam"] = joblib.load(MODELS_DIR / "family_classifier.joblib")
    return _models


def predict_need(category, req):
    df = pd.DataFrame(
        [
            {
                "category": category,
                "users": req["users"],
                "traffic_gb_month": req["traffic_gb_month"],
                "storage_gb": req["storage_gb"],
                "performance": req["performance"],
            }
        ]
    )
    X = engineer(df)
    m = _load()
    vcpu, ram = m["reg"].predict(X)[0]
    family = str(m["fam"].predict(X)[0])
    return max(1, math.ceil(vcpu)), max(1, math.ceil(ram)), family


def fleet(family, vcpu, ram, min_count, region):
    """Cheapest number of identical instances (min_count..20) of one family that covers vcpu and ram."""
    best = None
    for n in range(min_count, 21):
        need_c, need_r = math.ceil(vcpu / n), math.ceil(ram / n)
        for name, fam, c, r, base in pricing.EC2_CATALOG:
            if fam != family or c < need_c or r < need_r:
                continue
            price, source = pricing.ec2_hourly(name, base, region)
            monthly = n * price * pricing.HOURS_PER_MONTH
            if best is None or monthly < best["ec2_monthly"] - 1e-9:
                best = {
                    "instance_type": name,
                    "family": fam,
                    "count": n,
                    "vcpu_each": c,
                    "ram_each": r,
                    "ec2_monthly": monthly,
                    "source": source,
                }
            break  # catalog is sorted, so the first fit is the smallest
    return best


def storage_plan(category, storage_gb, n, region):
    if category in S3_CATEGORIES or storage_gb > 1000:
        cost = pricing.s3_monthly(storage_gb, region) + pricing.ebs_monthly(30 * n, region)
        return {
            "service": "Amazon S3 Standard for data + 30 GB gp3 root volume per instance",
            "gb": storage_gb,
            "monthly_usd": r2(cost),
        }
    gb = max(storage_gb, 8 * n)
    return {"service": "Amazon EBS gp3", "gb": gb, "monthly_usd": r2(pricing.ebs_monthly(gb, region))}


def database_plan(category, users, need_ram, storage_gb, region):
    if category in RDS_CATEGORIES:
        target = max(4, need_ram // 2)
        chosen = pricing.RDS_CATALOG[-1]
        for item in pricing.RDS_CATALOG:
            if item[2] >= target:
                chosen = item
                break
        name, _c, _r, hourly = chosen
        multi = users >= 10_000
        gb = max(20, int(storage_gb * 0.3))
        cost = pricing.rds_monthly(hourly, gb, multi, region)
        return {
            "service": "Amazon RDS (PostgreSQL or MySQL) " + name + (" Multi-AZ" if multi else " Single-AZ"),
            "monthly_usd": r2(cost),
            "note": "Database storage assumed to be 30% of your storage (minimum 20 GB).",
        }
    if category in DYNAMO_CATEGORIES:
        return {
            "service": "Amazon DynamoDB (on-demand capacity)",
            "monthly_usd": 0.0,
            "note": "Usage-based pricing. Not included in the estimate.",
        }
    if category == "Database":
        return {
            "service": "Self-managed database on the EC2 instances (Amazon RDS is the managed alternative)",
            "monthly_usd": 0.0,
            "note": "Compute and storage for the database are already in the EC2 and storage lines.",
        }
    return {"service": "No database needed", "monthly_usd": 0.0, "note": ""}


def _option(key, label, summary, f, category, req, db, region):
    n = f["count"]
    users = int(req["users"])
    st = storage_plan(category, int(req["storage_gb"]), n, region)
    use_lb = n > 1 or users > HA_USER_THRESHOLD
    comps = {
        "ec2": f["ec2_monthly"],
        "storage": st["monthly_usd"],
        "database": db["monthly_usd"],
        "load_balancer": pricing.alb_monthly(region) if use_lb else 0.0,
        "data_transfer": pricing.transfer_monthly(float(req["traffic_gb_month"]), region),
        "monitoring": pricing.cloudwatch_monthly(n),
    }
    comps = {k: r2(v) for k, v in comps.items()}
    total = r2(sum(comps.values()))
    savings = {"savings_plan_total": r2(total - comps["ec2"] * SAVINGS_PLAN_DISCOUNT)}
    savings["spot_total"] = (
        r2(total - comps["ec2"] * SPOT_DISCOUNT) if category in SPOT_CATEGORIES else None
    )
    return {
        "key": key,
        "label": label,
        "summary": summary,
        "compute": f["instance_type"] + " x " + str(n),
        "instance_type": f["instance_type"],
        "count": n,
        "family": f["family"],
        "vcpu_total": f["vcpu_each"] * n,
        "ram_total": f["ram_each"] * n,
        "storage": st,
        "uses_load_balancer": use_lb,
        "components": comps,
        "monthly_usd": total,
        "within_budget": total <= float(req["budget_usd_month"]),
        "savings": savings,
    }


def _serverless_option(category, req, region):
    users = int(req["users"])
    compute, requests = pricing.serverless_monthly(users, region)
    comps = {
        "lambda_api": compute,
        "storage": pricing.s3_monthly(int(req["storage_gb"]), region),
        "data_transfer": pricing.transfer_monthly(float(req["traffic_gb_month"]), region),
        "monitoring": pricing.cloudwatch_monthly(0),
    }
    comps = {k: r2(v) for k, v in comps.items()}
    total = r2(sum(comps.values()))
    return {
        "key": "serverless",
        "label": "Serverless",
        "summary": "AWS Lambda behind API Gateway with S3 storage. No servers to manage; you pay per request.",
        "compute": "Lambda (512 MB) + API Gateway HTTP API",
        "instance_type": None,
        "count": None,
        "family": "serverless",
        "vcpu_total": None,
        "ram_total": None,
        "storage": {"service": "Amazon S3 Standard", "gb": int(req["storage_gb"]), "monthly_usd": comps["storage"]},
        "uses_load_balancer": False,
        "components": comps,
        "monthly_usd": total,
        "within_budget": total <= float(req["budget_usd_month"]),
        "savings": {"savings_plan_total": None, "spot_total": None},
        "requests_per_month": int(requests),
    }


def build_recommendation(category, req):
    region = req["region"]
    perf = req["performance"]
    users = int(req["users"])
    budget = float(req["budget_usd_month"])

    ml_vcpu, ml_ram, family = predict_need(category, req)
    need_vcpu = max(ml_vcpu, int(req["cpu_vcpu"]))
    need_ram = max(ml_ram, int(req["ram_gb"]))
    min_count = 2 if (users >= HA_USER_THRESHOLD or perf == "high") else 1
    db = database_plan(category, users, need_ram, int(req["storage_gb"]), region)

    options, sources = [], set()

    def add(key, label, summary, f):
        if not f:
            return
        sources.add(f["source"])
        opt = _option(key, label, summary, f, category, req, db, region)
        if all((o["instance_type"], o["count"]) != (opt["instance_type"], opt["count"]) for o in options):
            options.append(opt)

    if category == "Serverless":
        options.append(_serverless_option(category, req, region))

    add("recommended", "Recommended",
        "Best match for the predicted workload family (" + family + ").",
        fleet(family, need_vcpu, need_ram, min_count, region))

    families = ["general", "compute", "memory"] + (["burstable"] if perf != "high" else [])
    cheapest = None
    for fam in families:
        f = fleet(fam, need_vcpu, need_ram, min_count, region)
        if f and (cheapest is None or f["ec2_monthly"] < cheapest["ec2_monthly"]):
            cheapest = f
    add("budget", "Budget",
        "Lowest EC2 cost across general, compute, memory and burstable families.", cheapest)

    add("performance", "High performance",
        "Recommended family with 50% extra capacity for spikes.",
        fleet(family, math.ceil(need_vcpu * 1.5), math.ceil(need_ram * 1.5), min_count, region))

    if not options:
        return {"options": []}

    by_cost = sorted(options, key=lambda o: o["monthly_usd"])
    fits = [o for o in by_cost if o["within_budget"]]
    if fits:
        verdict = "Within budget: " + fits[0]["label"] + " costs $" + format(fits[0]["monthly_usd"], ".2f") + " of your $" + format(budget, ".2f") + " monthly budget."
    else:
        verdict = "No option fits your budget. The cheapest is " + by_cost[0]["label"] + " at $" + format(by_cost[0]["monthly_usd"], ".2f") + ". Consider lower performance, fewer users or a cheaper region."

    price_source = "live" if sources == {"live"} else "reference"
    assumptions = [
        "Prices are USD, on-demand, Linux, shared tenancy, 730 hours per month. Taxes and support plans are excluded.",
        ("EC2 prices came from the AWS Price List API (live)." if price_source == "live"
         else "EC2 and RDS prices are a reference table of us-east-1 list prices, scaled by an approximate regional factor of "
              + str(pricing.factor(region)) + " for " + region + ". Check the AWS Pricing Calculator for exact figures."),
        "Final sizing is the larger of the ML prediction and your own CPU and RAM inputs.",
        "ML models were trained on SYNTHETIC data. Treat sizes as a starting point, not a measurement.",
        "At 1,000+ users or high performance, at least 2 instances are used for availability.",
        "Data transfer: first 100 GB per month free, then tiered internet-out pricing. CloudFront is recommended but not priced.",
        "Load balancer: one ALB with an average of 1 LCU. Monitoring: 5 custom metrics and 3 alarms per instance plus 5 GB of logs.",
        "Savings Plan (28% off EC2) and Spot (65% off EC2) are illustrative. Real discounts vary by instance, term and region. Spot can be interrupted.",
        "S3 and DynamoDB request charges are not included.",
    ]
    if category == "Serverless":
        assumptions.append("Serverless option assumes 30 requests per user per day, 200 ms at 512 MB per request, and the Lambda free tier.")

    networking = [
        "Amazon VPC with public subnets for the load balancer and private subnets for servers",
        "Security groups: allow only ports 80 and 443 publicly; restrict SSH to your own IP",
    ]
    if any(o["uses_load_balancer"] for o in options):
        networking.append("Application Load Balancer for traffic spread and health checks")
    if category in CDN_CATEGORIES:
        networking.append("Amazon CloudFront in front of the app to cache content and cut transfer cost (not priced)")
    monitoring = [
        "Amazon CloudWatch with the CloudWatch Agent for memory and disk metrics",
        "Alarms: CPU above 80%, failed status checks, and a monthly budget alarm",
    ]

    return {
        "ml": {
            "predicted_vcpu": ml_vcpu,
            "predicted_ram_gb": ml_ram,
            "predicted_family": family,
            "data_source": "synthetic",
        },
        "sizing": {
            "vcpu": need_vcpu,
            "ram_gb": need_ram,
            "basis": "Larger of the ML prediction and your input",
        },
        "region": region,
        "budget_usd": budget,
        "budget_verdict": verdict,
        "price_source": price_source,
        "options": by_cost if False else options,
        "database": db,
        "networking": networking,
        "monitoring": monitoring,
        "assumptions": assumptions,
    }
