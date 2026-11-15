DOCS = {
    "ec2": ("Amazon EC2", "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html"),
    "rds": ("Amazon RDS", "https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html"),
    "s3": ("Amazon S3", "https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html"),
    "cw": ("Amazon CloudWatch", "https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html"),
    "cfn": ("AWS CloudFormation", "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html"),
    "lambda": ("AWS Lambda", "https://docs.aws.amazon.com/lambda/latest/dg/welcome.html"),
    "vpc": ("Amazon VPC", "https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html"),
    "alb": ("Application Load Balancer", "https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html"),
    "iam": ("AWS IAM", "https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html"),
    "sp": ("Savings Plans", "https://aws.amazon.com/savingsplans/"),
    "calc": ("AWS Pricing Calculator", "https://calculator.aws/"),
}

GENERAL = {
    "ec2": (("ec2", "instance", "virtual machine", "server type"),
            "Amazon EC2 provides virtual servers. Families differ by purpose: burstable (t3) for light variable load, general (m5) for balanced workloads, compute (c5) for CPU-heavy work, memory (r5) for databases and analytics, and GPU (g4dn) for ML.", ["ec2"]),
    "rds": (("rds", "managed database"),
            "Amazon RDS runs a managed relational database (backups, patching, optional Multi-AZ failover). You choose an instance class, storage and whether to run it in two zones for availability.", ["rds"]),
    "s3": (("s3", "bucket", "object storage"),
           "Amazon S3 stores objects (files) cheaply and durably. It suits large data such as video and logs. Block public access unless you need a public site.", ["s3"]),
    "cw": (("cloudwatch", "metric", "alarm"),
           "CloudWatch collects metrics and logs and raises alarms. EC2 reports CPU and network by default, but memory and disk need the CloudWatch Agent.", ["cw"]),
    "cfn": (("cloudformation", "template", "stack"),
            "CloudFormation builds AWS resources from a template as one stack. Deleting the stack removes everything in it, which avoids forgotten billable leftovers.", ["cfn"]),
    "lambda": (("lambda", "serverless", "function"),
               "Lambda runs your code per request without servers. You pay for requests and run time, so low-traffic workloads are very cheap.", ["lambda"]),
    "vpc": (("vpc", "subnet", "security group", "network"),
            "A VPC is your private network on AWS. Public subnets hold internet-facing resources, private subnets hold databases, and security groups act as firewalls.", ["vpc", "alb"]),
    "iam": (("iam", "permission", "least privilege", "root"),
            "IAM controls who can do what. Use a non-root user with least privilege, enable MFA on root, and never share access keys.", ["iam"]),
    "savings": (("savings plan", "reserved", "spot", "discount"),
                "Savings Plans trade a 1 or 3 year commitment for lower on-demand rates. Spot uses spare capacity at a large discount but can be interrupted, so it suits fault-tolerant work.", ["sp", "calc"]),
}

PROJECT_TOPICS = [
    ("cost", ("cost", "price", "how much", "monthly", "expensive", "cheap", "estimate")),
    ("budget", ("budget", "afford", "over budget", "within")),
    ("why", ("why", "how did", "predict", "ml ", "model", "size", "sizing")),
    ("compare", ("compare", "difference", "which option", "best option", "recommend")),
    ("savings", ("saving", "save", "spot", "discount", "reduce")),
    ("database", ("database", "rds", "dynamo", "db ")),
    ("network", ("network", "load balancer", "cloudfront", "vpc")),
    ("monitor", ("monitor", "alarm", "cloudwatch", "alert")),
    ("synthetic", ("synthetic", "accurate", "reliable", "real data", "trust")),
]


def _money(x):
    return "$" + format(float(x), ".2f")


def _project_answer(topic, rec, project):
    opts = rec["options"]
    name = project["name"]
    if topic in ("cost", "budget"):
        lines = ["Estimated monthly cost for " + name + " in " + rec["region"] + " (prices: " + rec["price_source"] + "):"]
        for o in opts:
            c = o["components"]
            parts = ", ".join(k.replace("_", " ") + " " + _money(v) for k, v in c.items() if v)
            lines.append("- " + o["label"] + ": " + _money(o["monthly_usd"]) + " (" + o["compute"] + "; " + parts + ")")
        lines.append(rec["budget_verdict"])
        return "\n".join(lines), ["calc"]
    if topic == "why":
        ml, sz = rec["ml"], rec["sizing"]
        return ("The ML model predicted " + str(ml["predicted_vcpu"]) + " vCPU, " + str(ml["predicted_ram_gb"]) +
                " GB RAM and the '" + ml["predicted_family"] + "' family. Final sizing is " + str(sz["vcpu"]) + " vCPU and " +
                str(sz["ram_gb"]) + " GB RAM (the larger of the prediction and your input). Important: the model was trained on "
                "SYNTHETIC data, so treat this as a starting point and load-test before relying on it."), ["ec2"]
    if topic == "compare":
        cheapest = min(opts, key=lambda o: o["monthly_usd"])
        fits = [o for o in opts if o["within_budget"]]
        lines = ["Options for " + name + ":"]
        for o in opts:
            lines.append("- " + o["label"] + ": " + o["compute"] + ", " + _money(o["monthly_usd"]) + (" (in budget)" if o["within_budget"] else " (over budget)"))
        lines.append("Cheapest: " + cheapest["label"] + ". " + ("Options within budget: " + ", ".join(o["label"] for o in fits) + "." if fits else "None fit your budget."))
        return "\n".join(lines), ["ec2"]
    if topic == "savings":
        lines = ["Illustrative savings (not guaranteed; real discounts vary):"]
        for o in opts:
            s = o["savings"]
            if s.get("savings_plan_total") is not None:
                line = "- " + o["label"] + ": " + _money(o["monthly_usd"]) + " -> " + _money(s["savings_plan_total"]) + " with a Savings Plan"
                if s.get("spot_total") is not None:
                    line += ", " + _money(s["spot_total"]) + " with Spot (interruptible)"
                lines.append(line)
        if len(lines) == 1:
            lines.append("This project uses a serverless option, which is already pay-per-use.")
        return "\n".join(lines), ["sp", "calc"]
    if topic == "database":
        db = rec["database"]
        return db["service"] + ". " + db.get("note", ""), ["rds"]
    if topic == "network":
        return "Networking for " + name + ":\n" + "\n".join("- " + x for x in rec["networking"]), ["vpc", "alb"]
    if topic == "monitor":
        return "Monitoring for " + name + ":\n" + "\n".join("- " + x for x in rec["monitoring"]), ["cw"]
    if topic == "synthetic":
        return ("The ML models were trained on synthetic data generated from documented sizing rules, not measured from real AWS "
                "workloads. Their scores show they learned those rules. Prices come from a " + rec["price_source"] +
                " source. Use the Pricing Calculator and a load test before committing."), ["calc"]
    return None, []


def answer(message, rec=None, project=None):
    text = " " + message.lower().strip() + " "
    docs, parts = [], []

    if rec and project:
        for topic, words in PROJECT_TOPICS:
            if any(w in text for w in words):
                body, keys = _project_answer(topic, rec, project)
                if body:
                    parts.append(body)
                    docs += keys
                if len(parts) == 2:
                    break

    if not parts:
        for topic, (words, body, keys) in GENERAL.items():
            if any(w in text for w in words):
                parts.append(body)
                docs += keys
                break

    if not parts:
        if rec:
            msg = "I can answer about this project's cost, budget, sizing, comparison, savings, database, networking and monitoring, or explain EC2, RDS, S3, Lambda, VPC, IAM and CloudWatch. Try: 'Why this instance?' or 'How much will it cost?'"
        else:
            msg = "Select a project with a recommendation to ask about its cost and sizing. Without one I can only explain AWS services such as EC2, RDS, S3, Lambda, VPC, IAM, CloudWatch and CloudFormation."
        return {"answer": msg, "sources": []}

    seen, sources = set(), []
    for k in docs:
        if k in DOCS and k not in seen:
            seen.add(k)
            sources.append({"title": DOCS[k][0], "url": DOCS[k][1]})
    return {"answer": "\n\n".join(parts), "sources": sources}
