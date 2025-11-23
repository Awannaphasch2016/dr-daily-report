#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for eval CLI commands
"""

import pytest
import os
import json
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import Mock, patch, MagicMock

from dr_cli.commands.eval import (
    eval,
    generate_ground_truth,
    upload_dataset,
    eval_agent,
    eval_component
)


class TestEvalCLI:
    """Test suite for eval CLI commands"""

    def setup_method(self):
        """Setup test fixtures"""
        self.runner = CliRunner()
        self.test_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Cleanup test fixtures"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_eval_group_help(self):
        """Test that eval group shows help"""
        result = self.runner.invoke(eval, ['--help'])
        assert result.exit_code == 0
        assert 'Evaluation commands for offline LangSmith evaluation' in result.output
        assert 'generate-ground-truth' in result.output
        assert 'upload-dataset' in result.output
        assert 'agent' in result.output
        assert 'component' in result.output

    def test_generate_ground_truth_help(self):
        """Test generate-ground-truth help"""
        result = self.runner.invoke(eval, ['generate-ground-truth', '--help'])
        assert result.exit_code == 0
        assert '--num' in result.output
        assert '--ticker' in result.output
        assert '--quality-tier' in result.output

    def test_upload_dataset_help(self):
        """Test upload-dataset help"""
        result = self.runner.invoke(eval, ['upload-dataset', '--help'])
        assert result.exit_code == 0
        assert '--from' in result.output
        assert '--name' in result.output
        assert '--type' in result.output

    def test_eval_agent_help(self):
        """Test eval agent help"""
        result = self.runner.invoke(eval, ['agent', '--help'])
        assert result.exit_code == 0
        assert '--dataset' in result.output
        assert '--experiment' in result.output

    def test_eval_component_help(self):
        """Test eval component help"""
        result = self.runner.invoke(eval, ['component', '--help'])
        assert result.exit_code == 0
        assert '--dataset' in result.output
        assert 'report-generation' in result.output

    @patch('src.agent.TickerAnalysisAgent')
    @patch('src.database.TickerDatabase')
    @patch('dr_cli.commands.eval.sqlite3')
    def test_generate_ground_truth_creates_files(self, mock_sqlite, mock_db, mock_agent):
        """Test that generate-ground-truth creates JSON files"""
        # Mock database responses
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_sqlite.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock database rows
        mock_cursor.fetchall.return_value = [
            ('PTT', '2025-11-20', '{"indicators": {}, "prices": {}}', 'Test report')
        ]

        # Mock database get_historical_scores
        mock_db_instance = Mock()
        mock_db.return_value = mock_db_instance
        mock_db_instance.get_historical_scores.return_value = [{
            'date': '2025-11-20',
            'faithfulness_score': 0.85,
            'completeness_score': 0.80,
            'reasoning_quality_score': 0.82,
            'compliance_score': 0.90,
            'qos_score': 0.75,
            'cost_efficiency_score': 0.88
        }]

        # Run command
        result = self.runner.invoke(eval, [
            'generate-ground-truth',
            '--num', '1',
            '--output-dir', self.test_dir
        ])

        # Check success
        assert result.exit_code == 0
        assert 'Generated' in result.output

        # Check file created
        files = list(Path(self.test_dir).glob('ground_truth_*.json'))
        assert len(files) == 1

        # Check file content
        with open(files[0], 'r') as f:
            data = json.load(f)
            assert data['ticker'] == 'PTT'
            assert data['date'] == '2025-11-20'
            assert 'metadata' in data
            assert data['metadata']['quality_tier'] == 'mock'
            assert data['metadata']['status'] == 'DRAFT'

    @patch('src.agent.TickerAnalysisAgent')
    def test_generate_ground_truth_no_historical_data(self, mock_agent):
        """Test generate-ground-truth with no historical data"""
        with patch('dr_cli.commands.eval.sqlite3') as mock_sqlite:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_sqlite.connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = []

            result = self.runner.invoke(eval, [
                'generate-ground-truth',
                '--num', '5',
                '--output-dir', self.test_dir
            ])

            assert result.exit_code == 0
            assert 'No historical data found' in result.output

    @patch('src.langsmith_integration.get_langsmith_client')
    def test_upload_dataset_success(self, mock_get_client):
        """Test upload-dataset uploads to LangSmith"""
        # Create test ground truth file
        test_file = os.path.join(self.test_dir, 'ground_truth_PTT_2025-11-20.json')
        test_data = {
            'ticker': 'PTT',
            'date': '2025-11-20',
            'data': {
                'indicators': {'rsi': 55.71},
                'prices': {'close': 53.67}
            },
            'ground_truth_report': 'Test report',
            'metadata': {
                'quality_tier': 'mock',
                'status': 'DRAFT'
            }
        }

        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False)

        # Mock LangSmith client
        mock_client = Mock()
        mock_dataset = Mock()
        mock_dataset.id = 'test-dataset-id'
        mock_client.create_dataset.return_value = mock_dataset
        mock_get_client.return_value = mock_client

        # Run command
        result = self.runner.invoke(eval, [
            'upload-dataset',
            '--from', self.test_dir,
            '--name', 'test-dataset',
            '--type', 'agent'
        ])

        # Check success
        assert result.exit_code == 0
        assert 'Uploaded' in result.output

        # Check client was called
        mock_client.create_dataset.assert_called_once()
        mock_client.create_example.assert_called_once()

    @patch('src.langsmith_integration.get_langsmith_client')
    def test_upload_dataset_no_files(self, mock_get_client):
        """Test upload-dataset with no ground truth files"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        result = self.runner.invoke(eval, [
            'upload-dataset',
            '--from', self.test_dir,
            '--name', 'test-dataset',
            '--type', 'agent'
        ])

        assert result.exit_code == 0
        assert 'No ground truth files found' in result.output

    @patch('scripts.eval_agent.run_agent_evaluation')
    def test_eval_agent_command(self, mock_run_eval):
        """Test eval agent command"""
        mock_run_eval.return_value = {'status': 'success'}

        result = self.runner.invoke(eval, [
            'agent',
            '--dataset', 'test-dataset'
        ])

        assert result.exit_code == 0
        mock_run_eval.assert_called_once()

    @patch('scripts.eval_component.run_component_evaluation')
    def test_eval_component_command(self, mock_run_eval):
        """Test eval component command"""
        mock_run_eval.return_value = {'status': 'success'}

        result = self.runner.invoke(eval, [
            'component',
            'report-generation',
            '--dataset', 'test-dataset'
        ])

        assert result.exit_code == 0
        mock_run_eval.assert_called_once()

    def test_eval_component_invalid_component(self):
        """Test eval component with invalid component name"""
        result = self.runner.invoke(eval, [
            'component',
            'invalid-component',
            '--dataset', 'test-dataset'
        ])

        assert result.exit_code == 0
        assert 'Unknown component' in result.output

    @patch('src.agent.TickerAnalysisAgent')
    def test_generate_ground_truth_quality_tiers(self, mock_agent):
        """Test generate-ground-truth with different quality tiers"""
        with patch('dr_cli.commands.eval.sqlite3') as mock_sqlite:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_sqlite.connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = [
                ('PTT', '2025-11-20', '{"indicators": {}}', 'Test report')
            ]

            with patch('src.database.TickerDatabase'):
                # Test mock tier
                result = self.runner.invoke(eval, [
                    'generate-ground-truth',
                    '--num', '1',
                    '--quality-tier', 'mock',
                    '--output-dir', self.test_dir
                ])
                assert result.exit_code == 0

                # Test silver tier (not yet implemented)
                result = self.runner.invoke(eval, [
                    'generate-ground-truth',
                    '--num', '1',
                    '--quality-tier', 'silver',
                    '--output-dir', self.test_dir
                ])
                assert result.exit_code == 0
                assert 'not yet implemented' in result.output

    @patch('src.langsmith_integration.get_langsmith_client')
    def test_upload_dataset_agent_vs_component(self, mock_get_client):
        """Test upload-dataset with agent vs component type"""
        # Create test ground truth file
        test_file = os.path.join(self.test_dir, 'ground_truth_PTT_2025-11-20.json')
        test_data = {
            'ticker': 'PTT',
            'date': '2025-11-20',
            'data': {
                'indicators': {'rsi': 55.71},
                'prices': {'close': 53.67}
            },
            'ground_truth_report': 'Test report',
            'metadata': {'quality_tier': 'mock'}
        }

        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False)

        mock_client = Mock()
        mock_dataset = Mock()
        mock_dataset.id = 'test-id'
        mock_client.create_dataset.return_value = mock_dataset
        mock_get_client.return_value = mock_client

        # Test agent type - should only include ticker and date in inputs
        result = self.runner.invoke(eval, [
            'upload-dataset',
            '--from', self.test_dir,
            '--name', 'test-dataset',
            '--type', 'agent'
        ])

        assert result.exit_code == 0
        call_args = mock_client.create_example.call_args
        inputs = call_args[1]['inputs']
        assert 'ticker' in inputs
        assert 'date' in inputs
        # Agent type should NOT have indicators in inputs
        assert 'indicators' not in inputs

        # Reset mock
        mock_client.reset_mock()
        mock_client.create_dataset.return_value = mock_dataset

        # Test component type - should include all data in inputs
        result = self.runner.invoke(eval, [
            'upload-dataset',
            '--from', self.test_dir,
            '--name', 'test-dataset-component',
            '--type', 'component'
        ])

        assert result.exit_code == 0
        call_args = mock_client.create_example.call_args
        inputs = call_args[1]['inputs']
        assert 'ticker' in inputs
        assert 'date' in inputs
        # Component type SHOULD have indicators in inputs
        assert 'indicators' in inputs


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
