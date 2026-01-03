# -*- coding: utf-8 -*-
"""
Infrastructure tests for EventBridge Scheduler (v2 - New Architecture)

Tests that verify the EventBridge Scheduler schedule and Lambda target are correctly deployed.
These tests use the Scheduler API (not EventBridge Rules API).

Migration phases:
    Phase 1: This file created, tests SKIP if scheduler not deployed
    Phase 2: Tests run in parallel with legacy tests (both pass)
    Phase 3: Tests are primary verification (legacy tests fail as expected)
    Phase 4: Legacy test file deleted, this becomes the only test

Markers:
    @pytest.mark.integration - Requires real AWS access
    @pytest.mark.infrastructure - Infrastructure verification tests
"""

import pytest
import boto3
from botocore.exceptions import ClientError
import json


@pytest.mark.integration
class TestEventBridgeSchedulerV2:
    """Test suite for EventBridge Scheduler infrastructure (new architecture)"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up AWS clients"""
        self.scheduler_client = boto3.client('scheduler', region_name='ap-southeast-1')
        self.lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
        self.iam_client = boto3.client('iam', region_name='ap-southeast-1')

        # Schedule name (Phase 1-3: includes -v2, Phase 4: no suffix)
        # Try both names for flexibility during migration
        self.schedule_name_v2 = 'dr-daily-report-daily-ticker-fetch-v2-dev'
        self.schedule_name_final = 'dr-daily-report-daily-ticker-fetch-dev'
        self.schedule_group = 'default'

        self.lambda_name = 'dr-daily-report-ticker-scheduler-dev'
        self.iam_role_name = 'dr-daily-report-eventbridge-scheduler-role-dev'

        # Detect which schedule name exists
        self.schedule_name = self._detect_schedule_name()

    def _detect_schedule_name(self):
        """Detect which schedule name is active (v2 or final)"""
        try:
            self.scheduler_client.get_schedule(
                Name=self.schedule_name_v2,
                GroupName=self.schedule_group
            )
            return self.schedule_name_v2
        except ClientError:
            try:
                self.scheduler_client.get_schedule(
                    Name=self.schedule_name_final,
                    GroupName=self.schedule_group
                )
                return self.schedule_name_final
            except ClientError:
                pytest.skip("EventBridge Scheduler not deployed yet (Phase 1 incomplete)")

    def test_scheduler_schedule_exists(self):
        """Test that the EventBridge Scheduler schedule exists"""
        try:
            response = self.scheduler_client.get_schedule(
                Name=self.schedule_name,
                GroupName=self.schedule_group
            )
            assert response['Name'] in [self.schedule_name_v2, self.schedule_name_final], \
                f"Schedule name mismatch: {response['Name']}"
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                pytest.fail(f"EventBridge Scheduler schedule '{self.schedule_name}' does not exist")
            raise

    def test_scheduler_expression_and_timezone(self):
        """
        Test that the schedule expression is correct AND timezone is explicit

        This is the KEY TEST for migration - validates semantic clarity improvement!
        """
        response = self.scheduler_client.get_schedule(
            Name=self.schedule_name,
            GroupName=self.schedule_group
        )

        # Verify schedule expression (Bangkok time, not UTC!)
        expected_cron = 'cron(0 5 * * ? *)'  # 5 AM Bangkok (semantic clarity!)
        actual_cron = response['ScheduleExpression']

        assert actual_cron == expected_cron, \
            f"Schedule expression is '{actual_cron}', expected '{expected_cron}' (Bangkok time)"

        # NEW CAPABILITY: Verify explicit timezone (not possible with EventBridge Rules!)
        expected_timezone = 'Asia/Bangkok'
        actual_timezone = response.get('ScheduleExpressionTimezone', 'NOT_SET')

        assert actual_timezone == expected_timezone, \
            f"Timezone is '{actual_timezone}', expected '{expected_timezone}' (explicit timezone support)"

    def test_scheduler_state(self):
        """Test that the schedule state is correct for current migration phase"""
        response = self.scheduler_client.get_schedule(
            Name=self.schedule_name,
            GroupName=self.schedule_group
        )

        state = response['State']

        # Phase 1: Should be DISABLED
        # Phase 2-4: Should be ENABLED
        # We don't know which phase, so just verify it's a valid state
        assert state in ['ENABLED', 'DISABLED'], \
            f"Schedule state is '{state}', expected ENABLED or DISABLED"

        # Log current state for debugging
        print(f"Schedule state: {state}")

    def test_scheduler_lambda_target(self):
        """Test that the schedule targets the correct Lambda function"""
        response = self.scheduler_client.get_schedule(
            Name=self.schedule_name,
            GroupName=self.schedule_group
        )

        target = response.get('Target', {})

        # Verify Lambda ARN includes function name and :live alias
        target_arn = target.get('Arn', '')
        assert self.lambda_name in target_arn, \
            f"Lambda '{self.lambda_name}' not found in target ARN: {target_arn}"

        assert ':live' in target_arn, \
            f"Target should invoke :live alias, not $LATEST. Got: {target_arn}"

        # Verify IAM role ARN for invocation
        role_arn = target.get('RoleArn', '')
        assert self.iam_role_name in role_arn, \
            f"IAM role '{self.iam_role_name}' not found in target role ARN: {role_arn}"

    def test_scheduler_target_input_payload(self):
        """Test that the schedule has correct input payload for Lambda"""
        response = self.scheduler_client.get_schedule(
            Name=self.schedule_name,
            GroupName=self.schedule_group
        )

        target = response.get('Target', {})
        input_str = target.get('Input', '{}')

        input_payload = json.loads(input_str)

        # Verify required fields (same as EventBridge Rules payload)
        assert 'action' in input_payload, "Missing 'action' in target input"
        assert input_payload['action'] == 'precompute', \
            f"Action is '{input_payload['action']}', expected 'precompute'"

        assert input_payload.get('include_report') is True, \
            f"include_report is {input_payload.get('include_report')}, expected True"

    def test_scheduler_iam_role_exists(self):
        """Test that the Scheduler IAM role exists with correct trust policy"""
        try:
            response = self.iam_client.get_role(RoleName=self.iam_role_name)
            role = response['Role']

            assert role['RoleName'] == self.iam_role_name

            # Verify trust policy allows scheduler.amazonaws.com
            assume_role_policy = json.loads(
                role['AssumeRolePolicyDocument']
                if isinstance(role['AssumeRolePolicyDocument'], str)
                else json.dumps(role['AssumeRolePolicyDocument'])
            )

            statements = assume_role_policy.get('Statement', [])
            scheduler_trust_found = False

            for stmt in statements:
                principal = stmt.get('Principal', {})
                service = principal.get('Service', '')

                if service == 'scheduler.amazonaws.com' or 'scheduler.amazonaws.com' in service:
                    scheduler_trust_found = True
                    break

            assert scheduler_trust_found, \
                "IAM role does not have trust policy for scheduler.amazonaws.com"

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                pytest.fail(f"IAM role '{self.iam_role_name}' does not exist")
            raise

    def test_scheduler_iam_role_has_lambda_invoke_permission(self):
        """Test that the Scheduler IAM role has permission to invoke Lambda"""
        try:
            # Get inline policies (Terraform uses inline policy, not managed)
            response = self.iam_client.list_role_policies(RoleName=self.iam_role_name)
            policy_names = response.get('PolicyNames', [])

            assert len(policy_names) > 0, \
                f"IAM role '{self.iam_role_name}' has no inline policies"

            # Check each policy for lambda:InvokeFunction permission
            lambda_invoke_found = False

            for policy_name in policy_names:
                policy_response = self.iam_client.get_role_policy(
                    RoleName=self.iam_role_name,
                    PolicyName=policy_name
                )

                policy_doc = json.loads(
                    policy_response['PolicyDocument']
                    if isinstance(policy_response['PolicyDocument'], str)
                    else json.dumps(policy_response['PolicyDocument'])
                )

                for stmt in policy_doc.get('Statement', []):
                    actions = stmt.get('Action', [])
                    if isinstance(actions, str):
                        actions = [actions]

                    if 'lambda:InvokeFunction' in actions:
                        lambda_invoke_found = True
                        break

            assert lambda_invoke_found, \
                "IAM role does not have lambda:InvokeFunction permission"

        except ClientError as e:
            pytest.fail(f"Failed to check IAM role policies: {e}")

    def test_lambda_function_exists(self):
        """Test that the scheduler Lambda function exists"""
        try:
            response = self.lambda_client.get_function(FunctionName=self.lambda_name)
            assert response['Configuration']['FunctionName'] == self.lambda_name
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                pytest.fail(f"Lambda function '{self.lambda_name}' does not exist")
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

    def test_scheduler_retry_policy_configured(self):
        """Test that the schedule has retry policy for resilience"""
        response = self.scheduler_client.get_schedule(
            Name=self.schedule_name,
            GroupName=self.schedule_group
        )

        target = response.get('Target', {})
        retry_policy = target.get('RetryPolicy', {})

        # Verify retry policy exists
        assert retry_policy, "Retry policy should be configured for production resilience"

        # Verify max retry attempts
        max_retries = retry_policy.get('MaximumRetryAttempts', 0)
        assert max_retries >= 2, \
            f"Maximum retry attempts is {max_retries}, recommended at least 2"

        # Verify max event age
        max_age = retry_policy.get('MaximumEventAgeInSeconds', 0)
        assert max_age >= 3600, \
            f"Maximum event age is {max_age}s, recommended at least 3600s (1 hour)"


@pytest.mark.integration
class TestSchedulerLambdaEnvironment:
    """Test Lambda environment configuration for scheduler (reuse from legacy tests)"""

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
            'PDF_BUCKET_NAME',       # For caching
            'ENVIRONMENT',           # Environment identifier
            'OPENROUTER_API_KEY',    # For LLM report generation
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
