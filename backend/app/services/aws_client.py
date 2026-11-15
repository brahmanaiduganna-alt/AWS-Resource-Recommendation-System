import os

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, ProfileNotFound


def session(region=None):
    profile = os.getenv("AWS_PROFILE") or None
    return boto3.Session(
        profile_name=profile,
        region_name=region or os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    )


def status():
    """Who are we talking to AWS as? Never returns keys."""
    try:
        ident = session().client("sts").get_caller_identity()
    except (ProfileNotFound, NoCredentialsError):
        return {"connected": False, "reason": "No AWS credentials found. Do Part A and B of Step 7."}
    except ClientError as exc:
        return {"connected": False, "reason": "AWS rejected the credentials: " + exc.response["Error"]["Code"]}
    except BotoCoreError:
        return {"connected": False, "reason": "Cannot reach AWS. Check your internet connection."}

    arn = ident["Arn"]
    if arn.endswith(":root"):
        return {"connected": False, "root": True,
                "reason": "These are ROOT credentials. Create an IAM user and use its keys instead."}
    return {
        "connected": True,
        "profile": os.getenv("AWS_PROFILE") or "default",
        "identity": arn.split(":")[-1],
        "account_suffix": ident["Account"][-4:],
    }


def validate_template(body, region):
    """Ask AWS CloudFormation to check the template. Creates nothing."""
    try:
        cf = session(region).client("cloudformation")
        out = cf.validate_template(TemplateBody=body)
        return {
            "status": "valid",
            "message": "AWS accepted the template.",
            "capabilities": out.get("Capabilities", []),
            "capabilities_reason": out.get("CapabilitiesReason", ""),
        }
    except (ProfileNotFound, NoCredentialsError):
        return {"status": "skipped", "message": "No AWS credentials. Local checks only."}
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        msg = exc.response["Error"]["Message"]
        if code == "ValidationError":
            return {"status": "invalid", "message": msg}
        return {"status": "error", "message": code + ": " + msg}
    except BotoCoreError as exc:
        return {"status": "error", "message": "Could not reach AWS: " + type(exc).__name__}
