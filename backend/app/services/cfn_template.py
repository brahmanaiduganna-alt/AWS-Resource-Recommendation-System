import html
import json
import math
import re

MAX_BYTES = 51200
MAX_RESOURCES = 500
PSEUDO = {"AWS::Region", "AWS::AccountId", "AWS::StackName", "AWS::StackId",
          "AWS::NoValue", "AWS::Partition", "AWS::URLSuffix", "AWS::NotificationARNs"}
SUB_VAR = re.compile(r"\$\{([A-Za-z0-9:]+)(?:\.[A-Za-z0-9.]+)?\}")
AMI_PARAM = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"


def _safe(text):
    return re.sub(r"[^A-Za-z0-9 _.:/=+@-]", "-", str(text)).strip()[:100] or "project"


def _tags(name, pid, label=None):
    tags = [
        {"Key": "Project", "Value": name},
        {"Key": "ProjectId", "Value": pid},
        {"Key": "ManagedBy", "Value": "cloud-recommender"},
    ]
    if label:
        tags.append({"Key": "Name", "Value": label})
    return tags


def _ref(x):
    return {"Ref": x}


def _att(resource, attribute):
    return {"Fn::GetAtt": [resource, attribute]}


def _assume(service):
    return {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"Service": service}, "Action": "sts:AssumeRole"}],
    }


def _policy(policy_name, actions, resources):
    return {
        "PolicyName": policy_name,
        "PolicyDocument": {
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Action": actions, "Resource": resources}],
        },
    }


def _user_data(name):
    page = html.escape(name)
    lines = [
        "#!/bin/bash",
        "dnf install -y nginx amazon-cloudwatch-agent",
        "cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json <<'EOF'",
        '{"metrics":{"metrics_collected":{"mem":{"measurement":["mem_used_percent"]},"disk":{"measurement":["used_percent"],"resources":["/"]}}}}',
        "EOF",
        "/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s",
        'echo "<h1>' + page + '</h1><p>Deployed by Cloud Recommender</p>" > /usr/share/nginx/html/index.html',
        "systemctl enable --now nginx",
    ]
    return "\n".join(lines) + "\n"


def _bucket(name, pid):
    return {
        "Type": "AWS::S3::Bucket",
        "Properties": {
            "BucketEncryption": {"ServerSideEncryptionConfiguration": [
                {"ServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]},
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True, "BlockPublicPolicy": True,
                "IgnorePublicAcls": True, "RestrictPublicBuckets": True},
            "Tags": _tags(name, pid),
        },
    }


def _table(name, pid):
    return {
        "Type": "AWS::DynamoDB::Table",
        "Properties": {
            "BillingMode": "PAY_PER_REQUEST",
            "AttributeDefinitions": [{"AttributeName": "pk", "AttributeType": "S"}],
            "KeySchema": [{"AttributeName": "pk", "KeyType": "HASH"}],
            "Tags": _tags(name, pid),
        },
    }


def _server_template(project, rec, option, req):
    pid = str(project["_id"])
    name = _safe(project["name"])
    count = int(option["count"])
    use_lb = bool(option["uses_load_balancer"])
    db_text = rec["database"]["service"]
    use_rds = "RDS" in db_text
    use_ddb = "DynamoDB" in db_text
    use_s3 = "S3" in option["storage"]["service"]
    tags = _tags(name, pid)
    R = {}

    # ---- network ----
    R["Vpc"] = {"Type": "AWS::EC2::VPC", "Properties": {
        "CidrBlock": "10.0.0.0/16", "EnableDnsSupport": True, "EnableDnsHostnames": True,
        "Tags": _tags(name, pid, name + " vpc")}}
    R["Igw"] = {"Type": "AWS::EC2::InternetGateway", "Properties": {"Tags": tags}}
    R["IgwAttach"] = {"Type": "AWS::EC2::VPCGatewayAttachment",
                      "Properties": {"VpcId": _ref("Vpc"), "InternetGatewayId": _ref("Igw")}}
    R["PublicRouteTable"] = {"Type": "AWS::EC2::RouteTable",
                             "Properties": {"VpcId": _ref("Vpc"), "Tags": tags}}
    R["PublicRoute"] = {"Type": "AWS::EC2::Route", "DependsOn": "IgwAttach", "Properties": {
        "RouteTableId": _ref("PublicRouteTable"), "DestinationCidrBlock": "0.0.0.0/0",
        "GatewayId": _ref("Igw")}}
    for i, letter in enumerate("AB"):
        R["PublicSubnet" + letter] = {"Type": "AWS::EC2::Subnet", "Properties": {
            "VpcId": _ref("Vpc"), "CidrBlock": "10.0." + str(i) + ".0/24",
            "AvailabilityZone": {"Fn::Select": [i, {"Fn::GetAZs": ""}]},
            "MapPublicIpOnLaunch": True, "Tags": _tags(name, pid, name + " public " + letter)}}
        R["PublicAssoc" + letter] = {"Type": "AWS::EC2::SubnetRouteTableAssociation", "Properties": {
            "SubnetId": _ref("PublicSubnet" + letter), "RouteTableId": _ref("PublicRouteTable")}}
        if use_rds:
            R["PrivateSubnet" + letter] = {"Type": "AWS::EC2::Subnet", "Properties": {
                "VpcId": _ref("Vpc"), "CidrBlock": "10.0." + str(10 + i) + ".0/24",
                "AvailabilityZone": {"Fn::Select": [i, {"Fn::GetAZs": ""}]},
                "Tags": _tags(name, pid, name + " private " + letter)}}

    # ---- security groups (no SSH; use Session Manager) ----
    if use_lb:
        R["AlbSg"] = {"Type": "AWS::EC2::SecurityGroup", "Properties": {
            "GroupDescription": "Load balancer: HTTP from the internet", "VpcId": _ref("Vpc"),
            "SecurityGroupIngress": [{"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "CidrIp": "0.0.0.0/0"}],
            "Tags": tags}}
        inst_ingress = [{"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80,
                         "SourceSecurityGroupId": _ref("AlbSg")}]
    else:
        inst_ingress = [{"IpProtocol": "tcp", "FromPort": p, "ToPort": p, "CidrIp": "0.0.0.0/0"}
                        for p in (80, 443)]
    R["InstanceSg"] = {"Type": "AWS::EC2::SecurityGroup", "Properties": {
        "GroupDescription": "Application servers", "VpcId": _ref("Vpc"),
        "SecurityGroupIngress": inst_ingress, "Tags": tags}}

    # ---- optional data services ----
    if use_s3:
        R["DataBucket"] = _bucket(name, pid)
    if use_ddb:
        R["DataTable"] = _table(name, pid)
    if use_rds:
        match = re.search(r"db\.[a-z0-9]+\.[a-z0-9]+", db_text)
        R["DbSg"] = {"Type": "AWS::EC2::SecurityGroup", "Properties": {
            "GroupDescription": "Database: PostgreSQL from the application servers only",
            "VpcId": _ref("Vpc"),
            "SecurityGroupIngress": [{"IpProtocol": "tcp", "FromPort": 5432, "ToPort": 5432,
                                      "SourceSecurityGroupId": _ref("InstanceSg")}],
            "Tags": tags}}
        R["DbSubnetGroup"] = {"Type": "AWS::RDS::DBSubnetGroup", "Properties": {
            "DBSubnetGroupDescription": "Private subnets for the database",
            "SubnetIds": [_ref("PrivateSubnetA"), _ref("PrivateSubnetB")], "Tags": tags}}
        R["Database"] = {"Type": "AWS::RDS::DBInstance", "DeletionPolicy": "Delete", "Properties": {
            "Engine": "postgres",
            "DBInstanceClass": match.group(0) if match else "db.t3.medium",
            "AllocatedStorage": str(max(20, int(int(req["storage_gb"]) * 0.3))),
            "StorageType": "gp3", "StorageEncrypted": True,
            "MultiAZ": "Multi-AZ" in db_text,
            "MasterUsername": "dbadmin", "ManageMasterUserPassword": True,
            "DBSubnetGroupName": _ref("DbSubnetGroup"),
            "VPCSecurityGroups": [_ref("DbSg")],
            "PubliclyAccessible": False, "BackupRetentionPeriod": 1,
            "DeletionProtection": False, "Tags": tags}}

    # ---- instance role ----
    policies = []
    if use_s3:
        policies.append(_policy("BucketAccess", ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
                                [_att("DataBucket", "Arn"), {"Fn::Sub": "${DataBucket.Arn}/*"}]))
    if use_ddb:
        policies.append(_policy("TableAccess",
                                ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
                                 "dynamodb:DeleteItem", "dynamodb:Query"],
                                [_att("DataTable", "Arn")]))
    role_props = {
        "AssumeRolePolicyDocument": _assume("ec2.amazonaws.com"),
        "ManagedPolicyArns": [
            "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
            "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"],
        "Tags": tags,
    }
    if policies:
        role_props["Policies"] = policies
    R["InstanceRole"] = {"Type": "AWS::IAM::Role", "Properties": role_props}
    R["InstanceProfile"] = {"Type": "AWS::IAM::InstanceProfile",
                            "Properties": {"Roles": [_ref("InstanceRole")]}}

    # ---- servers ----
    if use_s3:
        volume_gb = 30
    else:
        volume_gb = int(option["storage"]["gb"] / count + 0.999)
    volume_gb = min(16384, max(8, volume_gb))
    R["LaunchTemplate"] = {"Type": "AWS::EC2::LaunchTemplate", "Properties": {"LaunchTemplateData": {
        "ImageId": _ref("LatestAmiId"),
        "InstanceType": option["instance_type"],
        "IamInstanceProfile": {"Arn": _att("InstanceProfile", "Arn")},
        "SecurityGroupIds": [_ref("InstanceSg")],
        "BlockDeviceMappings": [{"DeviceName": "/dev/xvda", "Ebs": {
            "VolumeSize": volume_gb, "VolumeType": "gp3", "Encrypted": True, "DeleteOnTermination": True}}],
        "MetadataOptions": {"HttpTokens": "required"},
        "UserData": {"Fn::Base64": _user_data(name)},
        "TagSpecifications": [
            {"ResourceType": "instance", "Tags": _tags(name, pid, name + " server")},
            {"ResourceType": "volume", "Tags": tags}],
    }}}
    asg_props = {
        "MinSize": str(count), "MaxSize": str(count), "DesiredCapacity": str(count),
        "LaunchTemplate": {"LaunchTemplateId": _ref("LaunchTemplate"),
                           "Version": _att("LaunchTemplate", "LatestVersionNumber")},
        "VPCZoneIdentifier": [_ref("PublicSubnetA"), _ref("PublicSubnetB")],
        "HealthCheckType": "ELB" if use_lb else "EC2",
        "HealthCheckGracePeriod": 300,
        "Tags": [dict(t, PropagateAtLaunch=True) for t in tags],
    }
    if use_lb:
        asg_props["TargetGroupARNs"] = [_ref("TargetGroup")]
    R["Asg"] = {"Type": "AWS::AutoScaling::AutoScalingGroup", "DependsOn": "PublicRoute",
                "Properties": asg_props}

    if use_lb:
        R["Alb"] = {"Type": "AWS::ElasticLoadBalancingV2::LoadBalancer", "DependsOn": "IgwAttach",
                    "Properties": {"Type": "application", "Scheme": "internet-facing",
                                   "SecurityGroups": [_ref("AlbSg")],
                                   "Subnets": [_ref("PublicSubnetA"), _ref("PublicSubnetB")],
                                   "Tags": tags}}
        R["TargetGroup"] = {"Type": "AWS::ElasticLoadBalancingV2::TargetGroup", "Properties": {
            "VpcId": _ref("Vpc"), "Port": 80, "Protocol": "HTTP", "TargetType": "instance",
            "HealthCheckPath": "/", "Tags": tags}}
        R["Listener"] = {"Type": "AWS::ElasticLoadBalancingV2::Listener", "Properties": {
            "LoadBalancerArn": _ref("Alb"), "Port": 80, "Protocol": "HTTP",
            "DefaultActions": [{"Type": "forward", "TargetGroupArn": _ref("TargetGroup")}]}}

    R["CpuAlarm"] = {"Type": "AWS::CloudWatch::Alarm", "Properties": {
        "AlarmDescription": "Average CPU above 80% for 10 minutes",
        "Namespace": "AWS/EC2", "MetricName": "CPUUtilization", "Statistic": "Average",
        "Period": 300, "EvaluationPeriods": 2, "Threshold": 80,
        "ComparisonOperator": "GreaterThanThreshold", "TreatMissingData": "notBreaching",
        "Dimensions": [{"Name": "AutoScalingGroupName", "Value": _ref("Asg")}]}}

    outputs = {"VpcId": {"Value": _ref("Vpc")}, "AutoScalingGroup": {"Value": _ref("Asg")}}
    if use_lb:
        outputs["LoadBalancerDNS"] = {"Value": _att("Alb", "DNSName")}
    if use_s3:
        outputs["BucketName"] = {"Value": _ref("DataBucket")}
    if use_rds:
        outputs["DatabaseEndpoint"] = {"Value": _att("Database", "Endpoint.Address")}
    if use_ddb:
        outputs["TableName"] = {"Value": _ref("DataTable")}

    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": name + " - " + option["label"] + " option, generated by Cloud Recommender",
        "Parameters": {"LatestAmiId": {
            "Type": "AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>", "Default": AMI_PARAM}},
        "Resources": R,
        "Outputs": outputs,
    }


def _serverless_template(project, rec, option, req):
    pid = str(project["_id"])
    name = _safe(project["name"])
    tags = _tags(name, pid)
    use_ddb = "DynamoDB" in rec["database"]["service"]
    R = {"DataBucket": _bucket(name, pid)}
    env = {"BUCKET_NAME": _ref("DataBucket")}
    policies = [_policy("BucketAccess", ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
                        [_att("DataBucket", "Arn"), {"Fn::Sub": "${DataBucket.Arn}/*"}])]
    if use_ddb:
        R["DataTable"] = _table(name, pid)
        env["TABLE_NAME"] = _ref("DataTable")
        policies.append(_policy("TableAccess",
                                ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
                                 "dynamodb:DeleteItem", "dynamodb:Query"],
                                [_att("DataTable", "Arn")]))
    code = "\n".join([
        "import json",
        "PROJECT = " + json.dumps(name),
        "def handler(event, context):",
        "    body = {'message': 'Hello from Cloud Recommender', 'project': PROJECT}",
        "    return {'statusCode': 200, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps(body)}",
    ])
    R["FunctionRole"] = {"Type": "AWS::IAM::Role", "Properties": {
        "AssumeRolePolicyDocument": _assume("lambda.amazonaws.com"),
        "ManagedPolicyArns": ["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"],
        "Policies": policies, "Tags": tags}}
    R["Function"] = {"Type": "AWS::Lambda::Function", "Properties": {
        "Runtime": "python3.12", "Handler": "index.handler", "MemorySize": 512, "Timeout": 10,
        "Role": _att("FunctionRole", "Arn"), "Code": {"ZipFile": code},
        "Environment": {"Variables": env}, "Tags": tags}}
    R["FunctionLogs"] = {"Type": "AWS::Logs::LogGroup", "Properties": {
        "LogGroupName": {"Fn::Sub": "/aws/lambda/${Function}"}, "RetentionInDays": 14}}
    R["HttpApi"] = {"Type": "AWS::ApiGatewayV2::Api", "Properties": {
        "Name": name + " api", "ProtocolType": "HTTP", "Target": _att("Function", "Arn"),
        "Tags": {"Project": name, "ProjectId": pid, "ManagedBy": "cloud-recommender"}}}
    R["InvokePermission"] = {"Type": "AWS::Lambda::Permission", "Properties": {
        "FunctionName": _ref("Function"), "Action": "lambda:InvokeFunction",
        "Principal": "apigateway.amazonaws.com",
        "SourceArn": {"Fn::Sub": "arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${HttpApi}/*/*"}}}
    R["ErrorsAlarm"] = {"Type": "AWS::CloudWatch::Alarm", "Properties": {
        "AlarmDescription": "Lambda reported errors",
        "Namespace": "AWS/Lambda", "MetricName": "Errors", "Statistic": "Sum",
        "Period": 300, "EvaluationPeriods": 1, "Threshold": 0,
        "ComparisonOperator": "GreaterThanThreshold", "TreatMissingData": "notBreaching",
        "Dimensions": [{"Name": "FunctionName", "Value": _ref("Function")}]}}

    outputs = {"ApiUrl": {"Value": _att("HttpApi", "ApiEndpoint")},
               "BucketName": {"Value": _ref("DataBucket")}}
    if use_ddb:
        outputs["TableName"] = {"Value": _ref("DataTable")}
    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": name + " - Serverless option, generated by Cloud Recommender",
        "Resources": R,
        "Outputs": outputs,
    }


def build_template(project, rec, option, req):
    if option["key"] == "serverless":
        return _serverless_template(project, rec, option, req)
    return _server_template(project, rec, option, req)


def summarize(template):
    return [{"id": k, "type": v["Type"]} for k, v in template["Resources"].items()]


def _refs(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "Ref" and isinstance(value, str):
                yield value
            elif key == "Fn::GetAtt":
                if isinstance(value, list) and value:
                    yield value[0]
                elif isinstance(value, str):
                    yield value.split(".")[0]
            elif key == "Fn::Sub":
                text = value if isinstance(value, str) else (value[0] if value else "")
                for found in SUB_VAR.findall(text):
                    yield found
            else:
                yield from _refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _refs(item)


def check_template(template):
    """Local checks. Returns a list of problems (empty list means OK)."""
    issues = []
    resources = template.get("Resources", {})
    compact = json.dumps(template, separators=(",", ":"))
    if len(compact.encode("utf-8")) > MAX_BYTES:
        issues.append("Template is larger than 51,200 bytes.")
    if not resources:
        issues.append("Template has no resources.")
    if len(resources) > MAX_RESOURCES:
        issues.append("Template has more than 500 resources.")

    known = set(resources) | set(template.get("Parameters", {})) | PSEUDO
    for name, body in resources.items():
        for target in sorted(set(_refs(body))):
            if target not in known:
                issues.append(name + " refers to an unknown item: " + target)
        deps = body.get("DependsOn", [])
        for dep in ([deps] if isinstance(deps, str) else deps):
            if dep not in resources:
                issues.append(name + " depends on a missing resource: " + dep)
        props = body.get("Properties", {})
        if body.get("Type") == "AWS::EC2::SecurityGroup":
            for rule in props.get("SecurityGroupIngress", []):
                if rule.get("CidrIp") == "0.0.0.0/0" and rule.get("FromPort", 0) <= 22 <= rule.get("ToPort", 0):
                    issues.append(name + " opens SSH (port 22) to the whole internet.")
        if "MasterUserPassword" in props:
            issues.append(name + " contains a hardcoded database password.")
    for out_name, out in template.get("Outputs", {}).items():
        for target in sorted(set(_refs(out))):
            if target not in known:
                issues.append("Output " + out_name + " refers to an unknown item: " + target)
    return issues

