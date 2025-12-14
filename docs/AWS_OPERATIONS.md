# AWS Operations Guide

Quick reference for common AWS service operations. Commands are tested and verified to work from WSL2 Ubuntu environment.

---

## EC2 Instance Access

### SSM Session Manager (Recommended for WSL2)

**Connect to instance (interactive shell):**
```bash
aws ssm start-session \
  --target i-0dab21bdf83ce9aaf \
  --region ap-southeast-1
```

**Port forward to remote service (e.g., Aurora MySQL):**
```bash
aws ssm start-session \
  --target i-0dab21bdf83ce9aaf \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{
    "host":["dr-daily-report-aurora-dev.cluster-c9a0288e4hqm.ap-southeast-1.rds.amazonaws.com"],
    "portNumber":["3306"],
    "localPortNumber":["3307"]
  }' \
  --region ap-southeast-1

# Then connect via localhost:
mysql -h 127.0.0.1 -P 3307 -u admin -p ticker_data

# Or inspect with VisiData (requires setup - see Aurora section below):
/tmp/aurora-vd.sh ticker_info 50
```

**Check instance SSM registration status:**
```bash
aws ssm describe-instance-information \
  --filters "Key=InstanceIds,Values=i-0dab21bdf83ce9aaf" \
  --region ap-southeast-1 \
  --query 'InstanceInformationList[0].[PingStatus,AgentVersion,PlatformName]' \
  --output table
```

**List all SSM-managed instances:**
```bash
aws ssm describe-instance-information \
  --region ap-southeast-1 \
  --query 'InstanceInformationList[*].[InstanceId,PingStatus,PlatformName,IPAddress]' \
  --output table
```

### EC2 Instance Information

**List all instances:**
```bash
aws ec2 describe-instances \
  --query 'Reservations[*].Instances[*].[InstanceId,Tags[?Key==`Name`].Value|[0],State.Name,PublicIpAddress,PrivateIpAddress]' \
  --output table
```

**Get instance details:**
```bash
aws ec2 describe-instances \
  --instance-ids i-0dab21bdf83ce9aaf \
  --query 'Reservations[0].Instances[0]' \
  --output json
```

**Check instance IAM role:**
```bash
aws ec2 describe-iam-instance-profile-associations \
  --filters "Name=instance-id,Values=i-0dab21bdf83ce9aaf" \
  --query 'IamInstanceProfileAssociations[0].IamInstanceProfile.Arn' \
  --output text
```

**Attach IAM instance profile:**
```bash
aws ec2 associate-iam-instance-profile \
  --instance-id i-0dab21bdf83ce9aaf \
  --iam-instance-profile Name=EC2-SSM-InstanceProfile
```

---

## Aurora MySQL Database

### Via Lambda Proxy (Works from WSL2)

**Interactive SQL shell:**
```bash
~/aurora-cli.sh --interactive
# Or:
~/aurora-cli.sh --query "SELECT symbol, status FROM precomputed_reports LIMIT 10"
```

**Execute single query:**
```bash
aws lambda invoke \
  --function-name dr-daily-report-scheduler-dev \
  --payload '{"action":"query","sql":"SELECT COUNT(*) FROM precomputed_reports"}' \
  /tmp/response.json && cat /tmp/response.json | jq '.body.results'
```

### Via SSH Tunnel (Requires SSM Port Forward)

**Prerequisites for VisiData (one-time setup):**
```bash
# Install system libraries
sudo apt-get install -y pkg-config libmysqlclient-dev default-libmysqlclient-dev

# Install Python packages
pip install visidata 'ibis-framework[mysql]'
```

**Start port forward (see EC2 section above), then:**
```bash
# Direct MySQL connection:
mysql -h 127.0.0.1 -P 3307 -u admin -p ticker_data

# VisiData for interactive table exploration (recommended):
~/aurora-vd.sh precomputed_reports 100                    # View 100 rows
~/aurora-vd.sh ticker_info 50                             # View 50 rows

# With date filtering (auto-detects date column):
~/aurora-vd.sh precomputed_reports 100 --exclude-today    # Exclude today's data
~/aurora-vd.sh daily_prices 200 --before 2025-12-13       # Only before specific date
~/aurora-vd.sh precomputed_reports 50 --after 2025-12-01  # Only after specific date
~/aurora-vd.sh ticker_info 100 --date 2025-12-12          # Exact date only

# Specify date column explicitly (if auto-detection fails):
~/aurora-vd.sh precomputed_reports 100 --exclude-today --date-column computed_at

# Or manual approach:
mysql -h 127.0.0.1 -P 3307 -u admin -pAuroraDevDb2025SecureX1 ticker_data \
  -e "SELECT * FROM daily_prices LIMIT 200" > /tmp/data.tsv && vd /tmp/data.tsv
```

**VisiData navigation:**
```
- ↓/↑: Navigate rows          - ←/→: Navigate columns
- _: Expand column width       - /: Search
- |: Filter by column value    - Shift+F: Frequency table
- q: Quit
```

**Troubleshooting VisiData + Aurora:**

*Why not use `vdsql 'mysql://...'` directly?*
- VisiData requires TTY (interactive terminal) which may not be available in all environments
- The `aurora-vd.sh` wrapper provides equivalent functionality with a single command
- Backend verification: Test ibis MySQL connection works independently:

```bash
python3 << 'EOF'
import ibis
con = ibis.mysql.connect(
    host='127.0.0.1', port=3307,
    user='admin', password='AuroraDevDb2025SecureX1',
    database='ticker_data'
)
print(f"✅ Connected to Aurora")
print(f"📊 Tables: {', '.join(con.list_tables())}")
EOF
```

*Common issues:*
- **Connection refused**: Check SSM port forward is running (see EC2 section)
- **Authentication failed**: Verify password in connection string
- **Empty result**: Check table exists and has data: `~/aurora-cli.sh --query "SHOW TABLES"`
- **Date filter returns no data**: Check available dates: `~/aurora-cli.sh --query "SELECT DISTINCT DATE(report_date) FROM precomputed_reports ORDER BY report_date DESC LIMIT 5"`
- **Date column not auto-detected**: Use `--date-column <name>` to specify manually

---

## Lambda Functions

### Invoke Function

**Synchronous invocation:**
```bash
aws lambda invoke \
  --function-name dr-daily-report-scheduler-dev \
  --payload '{"action":"query","sql":"SELECT 1"}' \
  /tmp/response.json

cat /tmp/response.json | jq '.'
```

**Asynchronous invocation:**
```bash
aws lambda invoke \
  --function-name dr-daily-report-scheduler-dev \
  --invocation-type Event \
  --payload '{"action":"schedule_all"}' \
  /tmp/response.json
```

### View Logs

**Tail recent logs:**
```bash
aws logs tail /aws/lambda/dr-daily-report-scheduler-dev \
  --follow \
  --region ap-southeast-1
```

**Filter logs for errors:**
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/dr-daily-report-scheduler-dev \
  --filter-pattern "ERROR" \
  --start-time $(($(date +%s) - 3600))000 \
  --region ap-southeast-1 \
  --query 'events[*].message' \
  --output text
```

**Search logs for specific pattern:**
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/dr-daily-report-precompute-dev \
  --filter-pattern "NVDA19" \
  --start-time $(($(date +%s) - 3600))000 \
  --region ap-southeast-1
```

### List Functions

```bash
aws lambda list-functions \
  --query 'Functions[*].[FunctionName,Runtime,LastModified]' \
  --output table
```

---

## IAM Policies & Roles

### Create Policy from JSON

```bash
aws iam create-policy \
  --policy-name SSMSessionManagerAccess \
  --policy-document file:///tmp/ssm-session-manager-policy.json
```

**Complete SSM Policy (includes interactive shell + port forwarding):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:StartSession",
        "ssm:TerminateSession",
        "ssm:ResumeSession",
        "ssm:DescribeSessions",
        "ssm:GetConnectionStatus"
      ],
      "Resource": [
        "arn:aws:ec2:*:*:instance/*",
        "arn:aws:ssm:*:*:document/SSM-SessionManagerRunShell",
        "arn:aws:ssm:*:*:document/AWS-StartPortForwardingSessionToRemoteHost"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssm:DescribeInstanceInformation",
        "ssm:GetCommandInvocation",
        "ssm:ListCommandInvocations",
        "ssm:ListCommands"
      ],
      "Resource": "*"
    }
  ]
}
```

### Update Existing Policy

```bash
# Create new policy version (updates existing policy)
aws iam create-policy-version \
  --policy-arn arn:aws:iam::755283537543:policy/SSMSessionManagerAccess \
  --policy-document file:///tmp/ssm-policy.json \
  --set-as-default
```

### Attach Policy to User

```bash
aws iam attach-user-policy \
  --user-name anak \
  --policy-arn arn:aws:iam::755283537543:policy/SSMSessionManagerAccess
```

### Create IAM Role

```bash
aws iam create-role \
  --role-name EC2-SSM-Role \
  --assume-role-policy-document file:///tmp/ec2-trust-policy.json

aws iam attach-role-policy \
  --role-name EC2-SSM-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
```

### Create Instance Profile

```bash
aws iam create-instance-profile \
  --instance-profile-name EC2-SSM-InstanceProfile

aws iam add-role-to-instance-profile \
  --instance-profile-name EC2-SSM-InstanceProfile \
  --role-name EC2-SSM-Role
```

---

## S3 Operations

### List Buckets

```bash
aws s3 ls
```

### Sync Local to S3

```bash
aws s3 sync ./local-dir s3://bucket-name/prefix/ --delete
```

### Download Single File

```bash
aws s3 cp s3://bucket-name/file.json /tmp/file.json
```

---

## CloudWatch Logs

### List Log Groups

```bash
aws logs describe-log-groups \
  --query 'logGroups[*].logGroupName' \
  --output table
```

### Filter Logs by Time Range

```bash
# Last hour
START_TIME=$(($(date +%s) - 3600))000
aws logs filter-log-events \
  --log-group-name /aws/lambda/function-name \
  --start-time $START_TIME
```

---

## Debugging Checklist

When encountering AWS service issues, verify in order:

### 1. Client/Code Layer
```bash
# Verify AWS CLI configured
aws sts get-caller-identity

# Check credentials
cat ~/.aws/credentials
env | grep AWS
```

### 2. Permission Layer
```bash
# Check user policies
aws iam list-attached-user-policies --user-name <username>

# Check role policies
aws iam list-attached-role-policies --role-name <rolename>

# Simulate policy (dry-run)
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::ACCOUNT:user/USERNAME \
  --action-names ssm:StartSession \
  --resource-arns "arn:aws:ec2:REGION:ACCOUNT:instance/*"
```

### 3. Network Layer (Client Side)
```bash
# Test HTTPS connectivity to AWS
curl -I https://ssm.ap-southeast-1.amazonaws.com

# Check DNS resolution
nslookup ssm.ap-southeast-1.amazonaws.com

# Test WSL2 network
ip route show
cat /etc/resolv.conf
```

### 4. Network Layer (AWS Side)
```bash
# Check security groups
aws ec2 describe-security-groups \
  --group-ids sg-095b9cacc26c9ac6a \
  --query 'SecurityGroups[0].{Ingress:IpPermissions,Egress:IpPermissionsEgress}'

# Check VPC routing
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=vpc-0fb04b10ef8c3d18b"

# Check if instance in public subnet
aws ec2 describe-subnets \
  --subnet-ids subnet-0e3861e4ea942da39 \
  --query 'Subnets[0].MapPublicIpOnLaunch'
```

### 5. Instance/Service Layer
```bash
# Check SSM agent status (via SSM if accessible)
aws ssm send-command \
  --instance-ids i-0dab21bdf83ce9aaf \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["systemctl status snap.amazon-ssm-agent.amazon-ssm-agent"]'

# Check instance metadata service (from within instance)
# curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
```

---

## Common Patterns

### Wait for Resource Ready

```bash
# Wait for Lambda function updated
aws lambda wait function-updated-v2 \
  --function-name dr-daily-report-scheduler-dev

# Wait for instance running
aws ec2 wait instance-running \
  --instance-ids i-0dab21bdf83ce9aaf
```

### Query with JMESPath

```bash
# Get specific fields
aws ec2 describe-instances \
  --instance-ids i-0dab21bdf83ce9aaf \
  --query 'Reservations[0].Instances[0].[InstanceId,State.Name,PublicIpAddress]' \
  --output table

# Filter results
aws lambda list-functions \
  --query 'Functions[?Runtime==`python3.11`].FunctionName'
```

### Pagination

```bash
# List all (auto-pagination)
aws s3api list-objects-v2 \
  --bucket my-bucket \
  --query 'Contents[*].[Key,Size]' \
  --output table \
  --no-paginate  # Disable pagination if needed
```

---

## Environment-Specific Endpoints

### Development
- Aurora: `dr-daily-report-aurora-dev.cluster-c9a0288e4hqm.ap-southeast-1.rds.amazonaws.com`
- Scheduler Lambda: `dr-daily-report-scheduler-dev`
- Precompute Lambda: `dr-daily-report-precompute-dev`
- Region: `ap-southeast-1`

### Staging
- (To be added)

### Production
- (To be added)

---

## References

- [AWS CLI Command Reference](https://awscli.amazonaws.com/v2/documentation/api/latest/index.html)
- [SSM Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html)
- [JMESPath Tutorial](https://jmespath.org/tutorial.html)
- [VisiData Documentation](https://www.visidata.org/docs/)
