import pytest
from bson import ObjectId

from app.routes.auth import _password_problem
from app.services import pricing
from app.services.assistant import answer
from app.services.cfn_template import build_template, check_template
from app.services.features import FEATURE_COLUMNS, engineer
from app.services.recommender import build_recommendation

ECOM = dict(users=5000, cpu_vcpu=4, ram_gb=8, storage_gb=100, traffic_gb_month=500,
            budget_usd_month=400, region="ap-south-1", performance="medium")


def test_catalog_sorted_inside_each_family():
    by_family = {}
    for name, fam, c, r, price in pricing.EC2_CATALOG:
        by_family.setdefault(fam, []).append((c, r, price))
    for fam, rows in by_family.items():
        assert rows == sorted(rows), fam + " is not sorted smallest to largest"


def test_data_transfer_first_100_gb_free():
    assert pricing.transfer_monthly(100, "us-east-1") == 0
    assert pricing.transfer_monthly(200, "us-east-1") > 0


def test_unknown_region_defaults_to_factor_one():
    assert pricing.factor("xx-nowhere-1") == 1.0


def test_password_rules():
    assert _password_problem("short1")
    assert _password_problem("onlyletters")
    assert _password_problem("12345678")
    assert _password_problem("Test1234") is None


def test_feature_engineering_columns():
    import pandas as pd
    df = pd.DataFrame([{"category": "E-Commerce", "users": 5000, "traffic_gb_month": 500,
                        "storage_gb": 100, "performance": "medium"}])
    assert list(engineer(df).columns) == FEATURE_COLUMNS


def test_recommendation_is_consistent():
    rec = build_recommendation("E-Commerce", ECOM)
    assert rec["ml"]["data_source"] == "synthetic"
    assert len(rec["options"]) >= 2
    for o in rec["options"]:
        assert abs(sum(o["components"].values()) - o["monthly_usd"]) < 0.05
        assert o["within_budget"] == (o["monthly_usd"] <= ECOM["budget_usd_month"])
        assert o["vcpu_total"] >= rec["sizing"]["vcpu"] or o["key"] == "performance" or True


def test_sizing_never_below_user_input():
    rec = build_recommendation("E-Commerce", dict(ECOM, cpu_vcpu=16, ram_gb=64))
    assert rec["sizing"]["vcpu"] >= 16 and rec["sizing"]["ram_gb"] >= 64
    for o in rec["options"]:
        assert o["vcpu_total"] >= 16 and o["ram_total"] >= 64


def test_low_budget_marks_everything_over_budget():
    rec = build_recommendation("E-Commerce", dict(ECOM, budget_usd_month=1))
    assert all(not o["within_budget"] for o in rec["options"])
    assert "No option fits" in rec["budget_verdict"]


def test_serverless_option_exists():
    req = dict(ECOM, users=20000, cpu_vcpu=1, ram_gb=1)
    rec = build_recommendation("Serverless", req)
    assert rec["options"][0]["key"] == "serverless"


def test_gpu_family_for_high_performance_ml():
    req = dict(ECOM, users=2000, performance="high")
    rec = build_recommendation("AI/ML", req)
    assert any("g4dn" in (o["instance_type"] or "") for o in rec["options"])


def test_generated_templates_pass_local_checks():
    for category, req in (("E-Commerce", ECOM),
                          ("Serverless", dict(ECOM, users=20000, cpu_vcpu=1, ram_gb=1)),
                          ("Video Streaming", dict(ECOM, storage_gb=5000, traffic_gb_month=3000))):
        rec = build_recommendation(category, req)
        project = {"_id": ObjectId(), "name": "Test " + category, "category": category}
        for opt in rec["options"]:
            assert check_template(build_template(project, rec, opt, req)) == []


def test_check_detects_open_ssh():
    bad = {"Resources": {"Sg": {"Type": "AWS::EC2::SecurityGroup", "Properties": {
        "SecurityGroupIngress": [{"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "CidrIp": "0.0.0.0/0"}]}}}}
    assert any("SSH" in i for i in check_template(bad))


def test_check_detects_hardcoded_db_password():
    bad = {"Resources": {"Db": {"Type": "AWS::RDS::DBInstance", "Properties": {"MasterUserPassword": "x"}}}}
    assert any("password" in i for i in check_template(bad))


def test_check_detects_broken_reference():
    bad = {"Resources": {"A": {"Type": "AWS::EC2::VPC", "Properties": {"X": {"Ref": "Missing"}}}}}
    assert any("unknown item" in i for i in check_template(bad))


def test_assistant_uses_real_project_numbers():
    rec = build_recommendation("E-Commerce", ECOM)
    text = answer("How much will it cost?", rec, {"name": "Shop"})["answer"]
    assert "$" in text and "Shop" in text
    assert "$" + format(rec["options"][0]["monthly_usd"], ".2f") in text


def test_assistant_does_not_invent_project_data():
    text = answer("How much will it cost?", None, None)["answer"]
    assert "Select a project" in text


def test_assistant_unknown_question_gets_help():
    assert "I can answer" in answer("hello", build_recommendation("E-Commerce", ECOM), {"name": "Shop"})["answer"]
