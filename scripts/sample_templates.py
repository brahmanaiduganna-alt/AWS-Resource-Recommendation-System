import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from bson import ObjectId  # noqa: E402
from app.services.cfn_template import build_template, check_template  # noqa: E402
from app.services.recommender import build_recommendation  # noqa: E402

SAMPLES = {
    "ecommerce": ("E-Commerce", dict(users=5000, cpu_vcpu=4, ram_gb=8, storage_gb=100,
                                     traffic_gb_month=500, budget_usd_month=400,
                                     region="ap-south-1", performance="medium")),
    "serverless": ("Serverless", dict(users=20000, cpu_vcpu=1, ram_gb=1, storage_gb=50,
                                      traffic_gb_month=200, budget_usd_month=200,
                                      region="ap-south-1", performance="medium")),
    "video": ("Video Streaming", dict(users=5000, cpu_vcpu=4, ram_gb=8, storage_gb=5000,
                                      traffic_gb_month=3000, budget_usd_month=2000,
                                      region="ap-south-1", performance="medium")),
}

out_dir = ROOT / "cloudformation"
out_dir.mkdir(exist_ok=True)
problems = 0
for key, (category, req) in SAMPLES.items():
    rec = build_recommendation(category, req)
    project = {"_id": ObjectId(), "name": "Sample " + key, "category": category}
    for opt in rec["options"]:
        template = build_template(project, rec, opt, req)
        issues = check_template(template)
        path = out_dir / ("sample-" + key + "-" + opt["key"] + ".json")
        path.write_text(json.dumps(template, indent=2), encoding="utf-8")
        status = "OK " if not issues else "BAD"
        print(status, path.name, len(template["Resources"]), "resources")
        for issue in issues:
            problems += 1
            print("    -", issue)
print("Problems found:", problems)
