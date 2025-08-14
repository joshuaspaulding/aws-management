# AWS CloudWatch Accountant

A Python CLI tool for monitoring and analyzing CloudWatch Logs costs across AWS Organization accounts. This tool helps you understand your CloudWatch Logs spending by providing cost summaries, visualizations, and cross-account monitoring capabilities.

## Features

- **Cross-Account Monitoring**: Monitor CloudWatch Logs costs across all accounts in your AWS Organization
- **Cost Analysis**: Calculate ingestion and storage costs for each log group
- **Visual Reports**: Generate PNG charts showing cost breakdowns
- **IAM Role Management**: Automatically set up required IAM roles for cross-account access
- **CLI Interface**: Easy-to-use command-line interface built with Typer

## Prerequisites

- Python 3.7+
- AWS CLI configured with appropriate permissions
- Access to AWS Organizations
- Member accounts must have `OrganizationAccountAccessRole` configured

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd aws-cloudwatch-accountant
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Dependencies

The following Python packages are required:
- `typer` - CLI framework
- `boto3` - AWS SDK for Python
- `tabulate` - Table formatting
- `matplotlib` - Chart generation

## Usage

### Setup IAM Roles

Before using the tool, you need to set up IAM roles in all member accounts:

```bash
python main.py setup
```

This command:
- Creates a custom IAM role (`CloudWatchCostMonitorRole`) in each account
- Configures cross-account trust policies
- Attaches minimal permissions for CloudWatch Logs and metrics access

### Cost Summary

Generate a cost summary for all log groups across accounts:

```bash
python main.py summarize --days 30
```

Options:
- `--days`: Number of days to analyze (default: 30)

### Generate Cost Charts

Create visual charts of your CloudWatch Logs costs:

```bash
python main.py graph --days 30
```

This generates three PNG files:
- `ingestion_costs.png` - Ingestion costs by log group
- `storage_costs.png` - Storage costs by log group  
- `total_costs.png` - Total costs by log group

## Cost Calculation

The tool calculates costs based on AWS CloudWatch Logs pricing:

- **Ingestion**: $0.50 per GB
- **Storage**: $0.03 per GB-month

Costs are calculated using CloudWatch metrics:
- `IncomingBytes` for ingestion costs
- `StoredBytes` for storage costs

## IAM Permissions

The tool requires the following permissions:

### Management Account
- `organizations:DescribeOrganization`
- `organizations:ListAccounts`
- `iam:CreateRole`
- `iam:UpdateAssumeRolePolicy`
- `iam:PutRolePolicy`

### Member Accounts
- `logs:DescribeLogGroups`
- `cloudwatch:GetMetricData`
- `cloudwatch:GetMetricStatistics`
- `cloudwatch:ListMetrics`

## Output Examples

### Cost Summary Table
```
┌─────────────┬──────────────────────┬─────────────────┬──────────────┬─────────────┐
│ Account     │ LogGroup             │ IngestionCost   │ StorageCost  │ TotalCost   │
├─────────────┼──────────────────────┼─────────────────┼──────────────┼─────────────┤
│ Production  │ /aws/lambda/app      │ $12.50          │ $0.45        │ $12.95      │
│ Staging     │ /aws/lambda/test     │ $5.20           │ $0.18        │ $5.38       │
└─────────────┴──────────────────────┴─────────────────┴──────────────┴─────────────┘
```

### Generated Charts
The tool creates three PNG files showing cost breakdowns across all log groups and accounts.

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure your AWS credentials have the required permissions
2. **Role Not Found**: Run the `setup` command first to create required IAM roles
3. **No Data**: Check that CloudWatch Logs are enabled and generating metrics

### Debug Mode

For detailed error information, check the AWS CloudTrail logs or run with verbose logging.

## Security Considerations

- The tool creates IAM roles with minimal required permissions
- Cross-account access is limited to CloudWatch Logs and metrics only
- No sensitive data is logged or stored locally

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions, please open an issue in the repository.
