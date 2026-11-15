from datetime import datetime, timedelta, timezone

from app.services.aws_client import session

GROUPS = {
    "cpu": ("CPU utilization", "%"),
    "network": ("Network traffic", "MB per period"),
    "memory": ("Memory used (CloudWatch Agent)", "%"),
    "disk": ("Disk used (CloudWatch Agent)", "%"),
    "requests": ("Load balancer requests", "count"),
    "latency": ("Target response time", "seconds"),
    "dbcpu": ("Database CPU", "%"),
    "invocations": ("Lambda invocations", "count"),
    "errors": ("Lambda errors", "count"),
    "duration": ("Lambda duration", "ms"),
}


def _q(qid, group, label, ns, metric, dims, stat, scale=1.0):
    return {"id": qid, "group": group, "label": label, "scale": scale,
            "query": {"Id": qid,
                      "MetricStat": {"Metric": {"Namespace": ns, "MetricName": metric, "Dimensions": dims},
                                     "Period": 300, "Stat": stat},
                      "ReturnData": True}}


def _dim(name, value):
    return [{"Name": name, "Value": value}]


def collect(run, hours):
    region = run["region"]
    sess = session(region)
    cf, cw, asg_client = sess.client("cloudformation"), sess.client("cloudwatch"), sess.client("autoscaling")

    items = cf.describe_stack_resources(StackName=run["stack_id"])["StackResources"]
    res = {r["LogicalResourceId"]: r for r in items}
    queries, notes = [], []

    if "Asg" in res:
        asg = res["Asg"]["PhysicalResourceId"]
        d = _dim("AutoScalingGroupName", asg)
        queries += [
            _q("cpu1", "cpu", "Average CPU", "AWS/EC2", "CPUUtilization", d, "Average"),
            _q("netin", "network", "Network in", "AWS/EC2", "NetworkIn", d, "Sum", 1e-6),
            _q("netout", "network", "Network out", "AWS/EC2", "NetworkOut", d, "Sum", 1e-6),
        ]
        groups = asg_client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg])["AutoScalingGroups"]
        ids = [i["InstanceId"] for g in groups for i in g["Instances"]][:3]
        found_mem = False
        for n, iid in enumerate(ids):
            for group, metric in (("memory", "mem_used_percent"), ("disk", "disk_used_percent")):
                listed = cw.list_metrics(Namespace="CWAgent", MetricName=metric,
                                         Dimensions=[{"Name": "InstanceId", "Value": iid}])["Metrics"]
                if listed:
                    queries.append(_q(group[:3] + str(n), group, iid, "CWAgent", metric,
                                      listed[0]["Dimensions"], "Average"))
                    found_mem = found_mem or group == "memory"
        if not found_mem:
            notes.append("Memory and disk metrics are not available yet. The CloudWatch Agent needs a few minutes after the servers start.")

    if "Alb" in res:
        arn = res["Alb"]["PhysicalResourceId"]
        if "loadbalancer/" in arn:
            d = _dim("LoadBalancer", arn.split("loadbalancer/")[1])
            queries += [
                _q("alb1", "requests", "Requests", "AWS/ApplicationELB", "RequestCount", d, "Sum"),
                _q("alb2", "latency", "Average response time", "AWS/ApplicationELB", "TargetResponseTime", d, "Average"),
            ]

    if "Database" in res:
        d = _dim("DBInstanceIdentifier", res["Database"]["PhysicalResourceId"])
        queries.append(_q("rds1", "dbcpu", "Database CPU", "AWS/RDS", "CPUUtilization", d, "Average"))

    if "Function" in res:
        d = _dim("FunctionName", res["Function"]["PhysicalResourceId"])
        queries += [
            _q("fn1", "invocations", "Invocations", "AWS/Lambda", "Invocations", d, "Sum"),
            _q("fn2", "errors", "Errors", "AWS/Lambda", "Errors", d, "Sum"),
            _q("fn3", "duration", "Average duration", "AWS/Lambda", "Duration", d, "Average"),
        ]

    period = 300 if hours <= 6 else 900
    for q in queries:
        q["query"]["MetricStat"]["Period"] = period

    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    data = {}
    if queries:
        pages = cw.get_paginator("get_metric_data").paginate(
            MetricDataQueries=[q["query"] for q in queries],
            StartTime=start, EndTime=end, ScanBy="TimestampAscending")
        for page in pages:
            for r in page["MetricDataResults"]:
                slot = data.setdefault(r["Id"], {"t": [], "v": []})
                slot["t"] += [t.isoformat() for t in r["Timestamps"]]
                slot["v"] += list(r["Values"])

    charts = {}
    for q in queries:
        got = data.get(q["id"], {"t": [], "v": []})
        title, unit = GROUPS[q["group"]]
        chart = charts.setdefault(q["group"], {"key": q["group"], "title": title, "unit": unit, "series": []})
        chart["series"].append({
            "label": q["label"],
            "timestamps": got["t"],
            "values": [round(v * q["scale"], 3) for v in got["v"]],
        })

    alarm_names = [r["PhysicalResourceId"] for r in items if r["ResourceType"] == "AWS::CloudWatch::Alarm"]
    alarms = []
    if alarm_names:
        for a in cw.describe_alarms(AlarmNames=alarm_names)["MetricAlarms"]:
            alarms.append({
                "name": a["AlarmName"], "state": a["StateValue"],
                "description": a.get("AlarmDescription", ""),
                "reason": a.get("StateReason", ""),
                "updated": a["StateUpdatedTimestamp"].isoformat(),
            })

    if not any(s["values"] for c in charts.values() for s in c["series"]):
        notes.append("No data points yet. Metrics usually appear 5 to 10 minutes after a deployment, and only while the resources are receiving traffic.")
    return {"hours": hours, "period_seconds": period, "charts": list(charts.values()),
            "alarms": alarms, "notes": notes}
