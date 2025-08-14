import typer
import boto3
from datetime import datetime, timedelta
from tabulate import tabulate
import botocore.exceptions
import json
import matplotlib.pyplot as plt

app = typer.Typer(help="AWS CloudWatch Logs Cost Monitor")

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

def calculate_costs(profile_name: str, days: int = 30):
    try:
        # Create session with specific profile
        session = boto3.Session(profile_name=profile_name)
        logs_client = session.client("logs")
        cw_client = session.client("cloudwatch")

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
        typer.echo(f"Client error in profile {profile_name}: {str(e)}")
        return []
    except Exception as e:
        typer.echo(f"Error in profile {profile_name}: {str(e)}")
        return []

@app.command()
def summarize(profiles: str = typer.Option("", help="Comma-separated list of AWS profiles to analyze"), days: int = typer.Option(30, help="Number of days to summarize costs for")):
    """Summarize CloudWatch Logs costs by profile and log group."""
    if not profiles:
        typer.echo("Please provide AWS profiles to analyze using --profiles option")
        return
    
    profile_list = [p.strip() for p in profiles.split(",")]
    summary = []
    
    for profile in profile_list:
        typer.echo(f"Analyzing profile: {profile}")
        costs = calculate_costs(profile, days)
        for cost in costs:
            summary.append({
                "Profile": profile,
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
def graph(profiles: str = typer.Option("", help="Comma-separated list of AWS profiles to analyze"), days: int = typer.Option(30, help="Number of days to graph costs for")):
    """Graph CloudWatch Logs costs by profile and log group using matplotlib (saves to PNG files)."""
    if not profiles:
        typer.echo("Please provide AWS profiles to analyze using --profiles option")
        return
    
    profile_list = [p.strip() for p in profiles.split(",")]
    all_costs = {}
    
    for profile in profile_list:
        typer.echo(f"Analyzing profile: {profile}")
        costs = calculate_costs(profile, days)
        for cost in costs:
            key = f"{profile}:{cost['LogGroup']}"
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
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.bar(labels, values)
        ax.set_title(title)
        ax.set_xlabel("Log Group (Profile:Group)")
        ax.set_ylabel("Cost ($)")
        ax.tick_params(axis='x', rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close(fig)

    # Save graphs
    save_bar_chart(ingestion, "Ingestion Costs by Log Group", "ingestion_costs.png")
    save_bar_chart(storage, "Storage Costs by Log Group", "storage_costs.png")
    save_bar_chart(total, "Total Costs by Log Group", "total_costs.png")

    typer.echo("Graphs saved as PNG files: ingestion_costs.png, storage_costs.png, total_costs.png")
    typer.echo("On macOS, you can open them with: open ingestion_costs.png (etc.)")

if __name__ == "__main__":
    app()
