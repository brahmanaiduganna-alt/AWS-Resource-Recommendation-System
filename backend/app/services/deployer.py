import os

from app.services.aws_client import session


def enabled():
    return os.getenv("DEPLOY_ENABLED", "false").strip().lower() == "true"


def cost_cap():
    try:
        return float(os.getenv("MAX_DEPLOY_MONTHLY_USD", "50"))
    except ValueError:
        return 50.0


def role_arn():
    name = os.getenv("CFN_ROLE_NAME", "CloudRecommenderCFNRole")
    account = session().client("sts").get_caller_identity()["Account"]
    return "arn:aws:iam::" + account + ":role/" + name


def stack_name(project_id):
    return "cr-" + str(project_id)


def map_status(aws_status):
    if aws_status.endswith("_IN_PROGRESS"):
        return "deleting" if aws_status.startswith("DELETE") else "creating"
    if aws_status == "CREATE_COMPLETE":
        return "deployed"
    if aws_status == "DELETE_COMPLETE":
        return "deleted"
    if aws_status == "DELETE_FAILED":
        return "delete_failed"
    return "failed"


def create_stack(name, body, region, tags):
    cf = session(region).client("cloudformation")
    out = cf.create_stack(
        StackName=name,
        TemplateBody=body,
        Capabilities=["CAPABILITY_IAM"],
        RoleARN=role_arn(),
        Tags=tags,
        TimeoutInMinutes=45,
    )
    return out["StackId"]


def describe(stack_id, region):
    from botocore.exceptions import ClientError

    cf = session(region).client("cloudformation")
    try:
        stack = cf.describe_stacks(StackName=stack_id)["Stacks"][0]
    except ClientError as exc:
        if "does not exist" in exc.response["Error"]["Message"]:
            return {"aws_status": "DELETE_COMPLETE", "reason": "", "outputs": []}
        raise
    outputs = [{"key": o["OutputKey"], "value": o["OutputValue"]} for o in stack.get("Outputs", [])]
    return {
        "aws_status": stack["StackStatus"],
        "reason": stack.get("StackStatusReason", ""),
        "outputs": outputs,
    }


def events(stack_id, region, limit=15):
    try:
        cf = session(region).client("cloudformation")
        items = cf.describe_stack_events(StackName=stack_id)["StackEvents"][:limit]
    except Exception:
        return []
    return [
        {
            "time": e["Timestamp"].isoformat(),
            "resource": e["LogicalResourceId"],
            "type": e["ResourceType"],
            "status": e["ResourceStatus"],
            "reason": e.get("ResourceStatusReason", ""),
        }
        for e in items
    ]


def delete_stack(stack_id, region):
    cf = session(region).client("cloudformation")
    cf.delete_stack(StackName=stack_id, RoleARN=role_arn())
