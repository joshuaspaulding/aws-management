import typer
import boto3
from datetime import datetime, timedelta
from tabulate import tabulate
import botocore.exceptions
import json
import matplotlib.pyplot as plt

app = typer.Typer(help="AWS CloudWatch Logs Cost Monitor")

ROLE_NAME = "CloudWatchCostMonitorRole"  # Custom role for monitoring

def get_organizations_client():
    return boto3.client("organizations")

def get_management_account_id():
    org_client = get_organizations_client()
    return org_client.describe_organization()["Organization"]["MasterAccountId"]

def list_accounts():
    org_client = get_organizations_client()
    accounts = []
    paginator = org_client.get_paginator("list_accounts")
    for page in paginator.paginate():
        accounts.extend(page["Accounts"])
    return accounts

def setup_role_in_account(account_id: str, management_account_id: str, is_management: bool = False):
    sts_client = boto3.client("sts")
    try:
        if is_management:
            # For management account, use current credentials
            iam_client = boto3.client("iam")
            caller_identity = sts_client.get_caller_identity()
            user_arn = caller_identity["Arn"]
            assume_role_policy = {
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"AWS": user_arn},
                    "Action": "sts:AssumeRole"
                }]
            }
        else:
            # Assume OrganizationAccountAccessRole for member accounts
            assumed_role = sts_client.assume_role(
                RoleArn=f"arn:aws:iam::{account_id}:role/OrganizationAccountAccessRole",
                RoleSessionName="CostMonitorSetup"
            )
            credentials = assumed_role["Credentials"]
            iam_client = boto3.client(
                "iam",
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"]
            )
            assume_role_policy = {
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"AWS": f"arn:aws:iam::{management_account_id}:root"},
                    "Action": "sts:AssumeRole"
                }]
            }

        # Define narrow policy for logs and metrics access
        role_policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": [
                    "logs:DescribeLogGroups",
                    "cloudwatch:GetMetricData",
                    "cloudwatch:GetMetricStatistics",
                    "cloudwatch:ListMetrics"
                ],
                "Resource": "*"
            }]
        }

        # Create inline policy document
        policy_document = json.dumps(role_policy)

        try:
            # Create the role if it doesn't exist
            iam_client.create_role(
                RoleName=ROLE_NAME,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy),
                Description="Role for cross-account CloudWatch Logs cost monitoring"
            )
            typer.echo(f"Role {ROLE_NAME} created in account {account_id}")
        except iam_client.exceptions.EntityAlreadyExistsException:
            # Update trust policy if role exists
            iam_client.update_assume_role_policy(
                RoleName=ROLE_NAME,
                PolicyDocument=json.dumps(assume_role_policy)
            )
            typer.echo(f"Role {ROLE_NAME} already exists; trust policy updated in account {account_id}")

        # Put inline policy (better than managed for custom narrow permissions)
        iam_client.put_role_policy(
            RoleName=ROLE_NAME,
            PolicyName="CloudWatchLogsCostAccess",
            PolicyDocument=policy_document
        )
        typer.echo(f"Policy attached to role in account {account_id}")

    except botocore.exceptions.ClientError as e:
        typer.echo(f"Error setting up role in account {account_id}: {str(e)}")

def assume_role(account_id: str):
    sts_client = boto3.client("sts")
    assumed_role = sts_client.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{ROLE_NAME}",
        RoleSessionName="CostMonitor"
    )
    return assumed_role["Credentials"]

def get_log_groups(client):
    log_groups = []
    paginator = client.get_paginator("describe_log_groups")
    for page in paginator.paginate():
        log_groups.extend(page["logGroups"])
    return log_groups

def get_metric_data(client, metric_name, log_group_name, start_time, end_time):
    response = client.get_metric_data(
        MetricDataQueries=[{
            "Id": "m1",
            "MetricStat": {
                "Metric": {
                    "Namespace": "AWS/Logs",
                    "MetricName": metric_name,
                    "Dimensions": [{"Name": "LogGroupName", "Value": log_group_name}]
                },
                "Period": 86400,
                "Stat": "Sum" if metric_name == "IncomingBytes" else "Average"
            },
            "ReturnData": True
        }],
        StartTime=start_time,
        EndTime=end_time
    )
    return response["MetricDataResults"][0]["Values"]

def calculate_costs(account_id: str, days: int = 30, management_id: str = None):
    try:
        if account_id == management_id:
            # Use current session for management account
            logs_client = boto3.client("logs")
            cw_client = boto3.client("cloudwatch")
        else:
            credentials = assume_role(account_id)
            logs_client = boto3.client(
                "logs",
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"]
            )
            cw_client = boto3.client(
                "cloudwatch",
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"]
            )

        log_groups = get_log_groups(logs_client)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

        costs = []
        for group in log_groups:
            group_name = group["logGroupName"]
            incoming_bytes = get_metric_data(cw_client, "IncomingBytes", group_name, start_time, end_time)
            stored_bytes = get_metric_data(cw_client, "StoredBytes", group_name, start_time, end_time)

            ingestion_gb = sum(incoming_bytes) / 1e9 if incoming_bytes else 0
            avg_storage_gb = sum(stored_bytes) / len(stored_bytes) / 1e9 if stored_bytes else 0
            storage_gb_month = avg_storage_gb * (days / 30)

            ingestion_cost = ingestion_gb * 0.50  # $0.50/GB
            storage_cost = storage_gb_month * 0.03  # $0.03/GB-month

            costs.append({
                "LogGroup": group_name,
                "IngestionCost": ingestion_cost,
                "StorageCost": storage_cost,
                "TotalCost": ingestion_cost + storage_cost
            })

        return costs
    except botocore.exceptions.ClientError as e:
        typer.echo(f"Client error in account {account_id}: {str(e)}")
        return []
    except Exception as e:
        typer.echo(f"Error in account {account_id}: {str(e)}")
        return []

@app.command()
def setup():
    """Setup IAM roles in all member accounts for cross-account access."""
    management_id = get_management_account_id()
    accounts = list_accounts()
    for account in accounts:
        if account["Status"] == "ACTIVE":
            is_mgmt = account["Id"] == management_id
            typer.echo(f"Setting up role in account {account['Id']} {'(management)' if is_mgmt else ''}")
            setup_role_in_account(account["Id"], management_id, is_mgmt)

@app.command()
def summarize(days: int = typer.Option(30, help="Number of days to summarize costs for")):
    """Summarize CloudWatch Logs costs by account and log group."""
    management_id = get_management_account_id()
    accounts = list_accounts()
    summary = []
    for account in accounts:
        if account["Status"] == "ACTIVE":
            account_id = account["Id"]
            account_name = account.get("Name", account_id)
            costs = calculate_costs(account_id, days, management_id)
            for cost in costs:
                summary.append({
                    "Account": account_name,
                    "LogGroup": cost["LogGroup"],
                    "IngestionCost": f"${cost['IngestionCost']:.2f}",
                    "StorageCost": f"${cost['StorageCost']:.2f}",
                    "TotalCost": f"${cost['TotalCost']:.2f}"
                })

    if summary:
        typer.echo(tabulate(summary, headers="keys", tablefmt="grid"))
    else:
        typer.echo("No costs found or access issues.")

@app.command()
def graph(days: int = typer.Option(30, help="Number of days to graph costs for")):
    """Graph CloudWatch Logs costs by account and log group using matplotlib (saves to PNG files)."""
    management_id = get_management_account_id()
    accounts = list_accounts()
    all_costs = {}
    for account in accounts:
        if account["Status"] == "ACTIVE":
            account_id = account["Id"]
            account_name = account.get("Name", account_id)
            costs = calculate_costs(account_id, days, management_id)
            for cost in costs:
                key = f"{account_name}:{cost['LogGroup']}"
                all_costs[key] = {
                    "Ingestion": cost["IngestionCost"],
                    "Storage": cost["StorageCost"],
                    "Total": cost["TotalCost"]
                }

    if not all_costs:
        typer.echo("No costs found or access issues.")
        return

    # Prepare data for graphs
    labels = list(all_costs.keys())
    ingestion = [all_costs[k]["Ingestion"] for k in labels]
    storage = [all_costs[k]["Storage"] for k in labels]
    total = [all_costs[k]["Total"] for k in labels]

    # Helper function to create and save bar chart
    def save_bar_chart(values, title, filename):
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(labels, values)
        ax.set_title(title)
        ax.set_xlabel("Log Group (Account:Group)")
        ax.set_ylabel("Cost ($)")
        ax.tick_params(axis='x', rotation=45)
        plt.tight_layout()
        plt.savefig(filename)
        plt.close(fig)

    # Save graphs
    save_bar_chart(ingestion, "Ingestion Costs by Log Group", "ingestion_costs.png")
    save_bar_chart(storage, "Storage Costs by Log Group", "storage_costs.png")
    save_bar_chart(total, "Total Costs by Log Group", "total_costs.png")

    typer.echo("Graphs saved as PNG files: ingestion_costs.png, storage_costs.png, total_costs.png")
    typer.echo("On macOS, you can open them with: open ingestion_costs.png (etc.)")

if __name__ == "__main__":
    app()
