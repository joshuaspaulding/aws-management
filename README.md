# AWS CloudWatch Accountant

A Python CLI tool for monitoring and analyzing CloudWatch Logs costs across multiple AWS accounts using different AWS profiles. This tool helps you understand your CloudWatch Logs spending by providing cost summaries, visualizations, and multi-profile monitoring capabilities.

## Features

- **Multi-Profile Monitoring**: Monitor CloudWatch Logs costs across multiple AWS accounts using different profiles
- **Cost Analysis**: Calculate ingestion and storage costs for each log group
- **Visual Reports**: Generate PNG charts showing cost breakdowns
- **CLI Interface**: Easy-to-use command-line interface built with Typer

## Prerequisites

- Python 3.7+
- AWS CLI configured with multiple profiles
- saml2aws configured for profile switching
- AWS credentials with permissions to:
  - Read CloudWatch Logs
  - Access CloudWatch metrics

## Installation

1. Clone this repository:
```bash
git clone https://github.com/joshuaspaulding/aws-management.git
cd aws-management
```

2. Create and activate a virtual environment:
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Verify installation:
```bash
python main.py --help
```

## Dependencies

The following Python packages are required:
- `typer` - CLI framework
- `boto3` - AWS SDK for Python
- `tabulate` - Table formatting
- `matplotlib` - Chart generation

## Usage

The tool provides two main commands that require you to specify AWS profiles:

### Summarize Costs

Generate a cost summary table for all log groups across specified AWS profiles:

```bash
python main.py summarize --profiles "prod,staging,dev" --days 30
```

Options:
- `--profiles`: Comma-separated list of AWS profiles to analyze (required)
- `--days`: Number of days to analyze (default: 30)

### Generate Charts

Create visual charts of your costs:

```bash
python main.py graph --profiles "prod,staging,dev" --days 30
```

This will generate three PNG files:
- `ingestion_costs.png` - Ingestion costs by log group
- `storage_costs.png` - Storage costs by log group  
- `total_costs.png` - Total costs by log group

## AWS Profile Setup

### Using saml2aws

1. Configure saml2aws for your AWS accounts:
```bash
saml2aws configure --profile prod
saml2aws configure --profile staging
saml2aws configure --profile dev
```

2. Login to each profile:
```bash
saml2aws login --profile prod
saml2aws login --profile staging
saml2aws login --profile dev
```

3. Verify profiles are working:
```bash
aws sts get-caller-identity --profile prod
aws sts get-caller-identity --profile staging
aws sts get-caller-identity --profile dev
```

## Cost Calculation

The tool calculates costs based on AWS CloudWatch Logs pricing:

- **Ingestion**: $0.50 per GB of data ingested
- **Storage**: $0.03 per GB-month of data stored

Costs are calculated over the specified time period and aggregated by log group and profile.

## Required AWS Permissions

Your AWS profiles need the following permissions:

**For CloudWatch Logs access:**
- `logs:DescribeLogGroups`

**For CloudWatch Metrics access:**
- `cloudwatch:GetMetricData`
- `cloudwatch:GetMetricStatistics`
- `cloudwatch:ListMetrics`

## Output Examples

### Cost Summary Table
```
+-------------+------------------+------------------+-------------+------------+
| Profile     | LogGroup         | IngestionCost    | StorageCost | TotalCost  |
+=============+==================+==================+=============+============+
| prod        | /aws/lambda/... | $12.50          | $0.45       | $12.95     |
| staging     | /aws/ecs/...    | $8.75           | $0.30       | $9.05      |
| dev         | /aws/lambda/... | $3.20           | $0.15       | $3.35      |
+-------------+------------------+------------------+-------------+------------+
```

### Generated Charts
The tool creates three PNG files showing cost breakdowns across all log groups in your specified profiles.

## Example Workflows

### Analyze Production and Staging Costs
```bash
python main.py summarize --profiles "prod,staging" --days 7
```

### Generate Monthly Cost Charts
```bash
python main.py graph --profiles "prod,staging,dev,test" --days 30
```

### Quick Daily Summary
```bash
python main.py summarize --profiles "prod" --days 1
```

## Troubleshooting

**"Please provide AWS profiles to analyze using --profiles option"**
- Make sure to specify the `--profiles` parameter with your AWS profile names

**"No costs found or access issues"**
- Verify your AWS profiles have the required permissions
- Check that you can access CloudWatch Logs and Metrics with each profile
- Ensure your saml2aws sessions are active

**Permission errors**
- Confirm your AWS profiles have access to CloudWatch services
- Verify you can list log groups with each profile

**Virtual environment issues**
- Make sure you've activated the virtual environment before running the tool
- Verify all dependencies are installed: `pip list`
- Try recreating the virtual environment if you encounter issues

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source and available under the MIT License.
