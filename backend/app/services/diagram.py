def _s(text):
    return str(text).replace('"', "'").replace("\n", " ")


def build_mermaid(rec, opt):
    """Return Mermaid flowchart text for one option of a recommendation."""
    db = rec["database"]["service"]
    net = " ".join(rec["networking"])
    lines = ["flowchart TD", '  U["Users"]']

    if opt["key"] == "serverless":
        lines += [
            '  API["Amazon API Gateway (HTTP API)"]',
            '  FN["AWS Lambda (512 MB)"]',
            '  S3[("Amazon S3")]',
            '  CW["Amazon CloudWatch"]',
            "  U --> API",
            "  API --> FN",
            "  FN --> S3",
            "  FN -.-> CW",
        ]
        if "DynamoDB" in db:
            lines += ['  DDB[("Amazon DynamoDB")]', "  FN --> DDB"]
        return "\n".join(lines)

    count = int(opt["count"])
    shown = min(count, 3)
    entry = "U"

    if "CloudFront" in net:
        lines += ['  CF["Amazon CloudFront"]', "  U --> CF"]
        entry = "CF"
    if opt["uses_load_balancer"]:
        lines += ['  ALB["Application Load Balancer"]', "  " + entry + " --> ALB"]
        entry = "ALB"

    lines.append('  subgraph FLEET["EC2 fleet: ' + _s(opt["instance_type"]) + " x " + str(count) + '"]')
    for i in range(shown):
        lines.append('    E' + str(i) + '["EC2 ' + _s(opt["instance_type"]) + '"]')
    if count > shown:
        lines.append('    EM["+ ' + str(count - shown) + ' more instances"]')
    lines.append("  end")
    for i in range(shown):
        lines.append("  " + entry + " --> E" + str(i))

    lines.append('  ST[("' + _s(opt["storage"]["service"]) + '")]')
    lines.append("  E0 --> ST")

    if "RDS" in db or "DynamoDB" in db:
        lines.append('  DB[("' + _s(db) + '")]')
        for i in range(shown):
            lines.append("  E" + str(i) + " --> DB")

    lines += ['  CW["Amazon CloudWatch"]', "  E0 -.-> CW"]
    return "\n".join(lines)
