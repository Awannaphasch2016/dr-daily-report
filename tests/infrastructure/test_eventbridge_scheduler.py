# -*- coding: utf-8 -*-
"""
Infrastructure tests for EventBridge Scheduler

Tests that verify the EventBridge rule and Lambda target are correctly deployed.
These tests require AWS credentials with EventBridge read permissions.

Markers:
    @pytest.mark.integration - Requires real AWS access
    @pytest.mark.infrastructure - Infrastructure verification tests
"""

import pytest
import boto3
from botocore.exceptions import ClientError


@pytest.mark.integration
class TestEventBridgeScheduler:
    """Test suite for EventBridge scheduler infrastructure"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up AWS clients"""
        self.events_client = boto3.client('events', region_name='ap-southeast-1')
        self.lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
        self.rule_name = 'dr-daily-report-daily-ticker-fetch-dev'
        self.lambda_name = 'dr-daily-report-ticker-scheduler-dev'

    def test_eventbridge_rule_exists(self):
        """Test that the EventBridge rule exists"""
        try:
            response = self.events_client.describe_rule(Name=self.rule_name)
            assert response['Name'] == self.rule_name, f"Rule name mismatch: {response['Name']}"
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                pytest.fail(f"EventBridge rule '{self.rule_name}' does not exist")
            raise

    def test_eventbridge_rule_is_enabled(self):
        """Test that the EventBridge rule is enabled"""
        response = self.events_client.describe_rule(Name=self.rule_name)
        assert response['State'] == 'ENABLED', f"Rule state is {response['State']}, expected ENABLED"

    def test_eventbridge_schedule_expression(self):
        """Test that the schedule expression is correct (8 AM Bangkok = 01:00 UTC)"""
        response = self.events_client.describe_rule(Name=self.rule_name)

        # Should be cron(0 1 * * ? *) for 01:00 UTC daily
        expected_cron = 'cron(0 1 * * ? *)'
        assert response['ScheduleExpression'] == expected_cron, \
            f"Schedule expression is '{response['ScheduleExpression']}', expected '{expected_cron}'"

    def test_eventbridge_target_exists(self):
        """Test that the EventBridge rule has a Lambda target"""
        response = self.events_client.list_targets_by_rule(Rule=self.rule_name)
        targets = response.get('Targets', [])

        assert len(targets) > 0, f"No targets found for rule '{self.rule_name}'"

        # Verify the target is our Lambda function
        target_arns = [t['Arn'] for t in targets]
        lambda_target_found = any(self.lambda_name in arn for arn in target_arns)
        assert lambda_target_found, \
            f"Lambda '{self.lambda_name}' not found in targets: {target_arns}"

    def test_eventbridge_target_input_payload(self):
        """Test that the EventBridge target has correct input payload"""
        response = self.events_client.list_targets_by_rule(Rule=self.rule_name)
        targets = response.get('Targets', [])

        assert len(targets) > 0, "No targets found"

        # Find the Lambda target and check its input
        lambda_target = next((t for t in targets if self.lambda_name in t['Arn']), None)
        assert lambda_target is not None, f"Lambda target not found"

        import json
        input_payload = json.loads(lambda_target.get('Input', '{}'))

        # Verify required fields
        assert 'action' in input_payload, "Missing 'action' in target input"
        assert input_payload['action'] == 'precompute', \
            f"Action is '{input_payload['action']}', expected 'precompute'"
        assert input_payload.get('include_report') is True, \
            f"include_report is {input_payload.get('include_report')}, expected True"

    def test_lambda_function_exists(self):
        """Test that the scheduler Lambda function exists"""
        try:
            response = self.lambda_client.get_function(FunctionName=self.lambda_name)
            assert response['Configuration']['FunctionName'] == self.lambda_name
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                pytest.fail(f"Lambda function '{self.lambda_name}' does not exist")
            raise

    def test_lambda_has_eventbridge_permission(self):
        """Test that Lambda has permission for EventBridge to invoke it"""
        try:
            response = self.lambda_client.get_policy(FunctionName=self.lambda_name)

            import json
            policy = json.loads(response['Policy'])
            statements = policy.get('Statement', [])

            # Find EventBridge invoke permission
            eventbridge_permission = None
            for stmt in statements:
                if (stmt.get('Principal', {}).get('Service') == 'events.amazonaws.com' and
                    'lambda:InvokeFunction' in stmt.get('Action', [])):
                    eventbridge_permission = stmt
                    break

            assert eventbridge_permission is not None, \
                "No EventBridge invoke permission found in Lambda policy"

            # Verify the permission references our rule
            source_arn = eventbridge_permission.get('Condition', {}).get('ArnLike', {}).get('AWS:SourceArn', '')
            assert self.rule_name in source_arn, \
                f"Permission source ARN doesn't reference rule '{self.rule_name}': {source_arn}"

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                pytest.fail("No resource policy found on Lambda function")
            raise

    def test_lambda_timeout_sufficient_for_precompute(self):
        """Test that Lambda timeout is sufficient for precomputing all tickers"""
        response = self.lambda_client.get_function_configuration(FunctionName=self.lambda_name)
        timeout = response['Timeout']

        # Precomputing ~47 tickers with LLM reports takes time
        # Minimum recommended: 300 seconds (5 minutes)
        min_timeout = 300
        assert timeout >= min_timeout, \
            f"Lambda timeout is {timeout}s, recommended minimum is {min_timeout}s for precompute"

    def test_lambda_memory_adequate(self):
        """Test that Lambda has adequate memory for LLM operations"""
        response = self.lambda_client.get_function_configuration(FunctionName=self.lambda_name)
        memory = response['MemorySize']

        # LLM operations need adequate memory
        # Minimum recommended: 512 MB
        min_memory = 512
        assert memory >= min_memory, \
            f"Lambda memory is {memory}MB, recommended minimum is {min_memory}MB"


@pytest.mark.integration
class TestSchedulerLambdaEnvironment:
    """Test Lambda environment configuration for scheduler"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up AWS client"""
        self.lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
        self.lambda_name = 'dr-daily-report-ticker-scheduler-dev'

    def test_required_env_vars_present(self):
        """Test that required environment variables are configured"""
        response = self.lambda_client.get_function_configuration(FunctionName=self.lambda_name)
        env_vars = response.get('Environment', {}).get('Variables', {})

        required_vars = [
            'PDF_BUCKET_NAME',  # For caching
            'ENVIRONMENT',      # Environment identifier
            'OPENROUTER_API_KEY',  # For LLM report generation
        ]

        missing_vars = [var for var in required_vars if var not in env_vars]
        assert len(missing_vars) == 0, \
            f"Missing required environment variables: {missing_vars}"

    def test_aurora_env_vars_when_enabled(self):
        """Test Aurora environment variables are present when Aurora is enabled"""
        response = self.lambda_client.get_function_configuration(FunctionName=self.lambda_name)
        env_vars = response.get('Environment', {}).get('Variables', {})

        # If AURORA_HOST is set, verify other Aurora vars
        if env_vars.get('AURORA_HOST'):
            aurora_vars = ['AURORA_HOST', 'AURORA_PORT', 'AURORA_DATABASE', 'AURORA_USER']
            missing_vars = [var for var in aurora_vars if var not in env_vars or not env_vars[var]]
            assert len(missing_vars) == 0, \
                f"Aurora is configured but missing variables: {missing_vars}"

    def test_vpc_config_for_aurora(self):
        """Test Lambda has VPC configuration when Aurora is enabled"""
        response = self.lambda_client.get_function_configuration(FunctionName=self.lambda_name)
        env_vars = response.get('Environment', {}).get('Variables', {})
        vpc_config = response.get('VpcConfig', {})

        # If Aurora is configured, Lambda should be in VPC
        if env_vars.get('AURORA_HOST'):
            subnet_ids = vpc_config.get('SubnetIds', [])
            security_group_ids = vpc_config.get('SecurityGroupIds', [])

            assert len(subnet_ids) > 0, \
                "Lambda should have subnet configuration for Aurora access"
            assert len(security_group_ids) > 0, \
                "Lambda should have security group for Aurora access"
