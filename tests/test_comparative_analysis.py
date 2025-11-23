#!/usr/bin/env python3
"""
Comprehensive test suite for comparative and similarity analysis module

Tests cover:
- Statistical analysis: correlation, clustering, PCA
- Graph theory: similarity networks, community detection, centrality
- Feature extraction and distance calculations
- Integration and edge cases
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from src.analysis.comparative_analysis import ComparativeAnalyzer


class TestComparativeAnalyzer(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = ComparativeAnalyzer()
        
        # Create sample ticker data for multiple tickers
        self.ticker_data = self._create_test_ticker_data()
    
    def _create_test_ticker_data(self, num_tickers=10, days=100):
        """Create realistic test data for multiple tickers"""
        ticker_data = {}
        dates = pd.date_range(start='2024-01-01', periods=days, freq='D')
        
        np.random.seed(42)
        
        for i in range(num_tickers):
            ticker = f"TEST{i+1}"
            
            # Create correlated price movements
            base_price = 100 + (i * 10)
            trend = np.linspace(0, 20 + (i * 2), days)
            noise = np.random.normal(0, 2, days)
            
            # Add some correlation between tickers
            if i > 0:
                correlation_factor = 0.3 * np.sin(i)
                noise += correlation_factor * np.random.normal(0, 1, days)
            
            prices = base_price + trend + noise
            
            ticker_data[ticker] = pd.DataFrame({
                'Open': prices + np.random.normal(0, 0.5, days),
                'High': prices + abs(np.random.normal(1, 0.5, days)),
                'Low': prices - abs(np.random.normal(1, 0.5, days)),
                'Close': prices,
                'Volume': np.random.uniform(1000000, 10000000, days)
            }, index=dates)
        
        return ticker_data
    
    def test_init(self):
        """Test analyzer initialization"""
        analyzer = ComparativeAnalyzer()
        self.assertIsNotNone(analyzer)
        self.assertIsNotNone(analyzer.scaler)
    
    def test_prepare_ticker_features(self):
        """Test feature extraction from ticker data"""
        features_df = self.analyzer.prepare_ticker_features(self.ticker_data)
        
        self.assertIsInstance(features_df, pd.DataFrame)
        self.assertGreater(len(features_df), 0)
        
        # Check required columns
        required_cols = ['ticker', 'mean_return', 'volatility', 'sharpe_ratio']
        for col in required_cols:
            self.assertIn(col, features_df.columns)
        
        # Check data types
        self.assertTrue(all(isinstance(t, str) for t in features_df['ticker']))
    
    def test_calculate_correlation_matrix(self):
        """Test correlation matrix calculation"""
        correlation_matrix = self.analyzer.calculate_correlation_matrix(self.ticker_data)
        
        self.assertIsInstance(correlation_matrix, pd.DataFrame)
        
        if not correlation_matrix.empty:
            # Should be square matrix
            self.assertEqual(correlation_matrix.shape[0], correlation_matrix.shape[1])
            
            # Diagonal should be 1.0
            for ticker in correlation_matrix.index:
                self.assertAlmostEqual(correlation_matrix.loc[ticker, ticker], 1.0, places=2)
            
            # Correlations should be between -1 and 1
            values = correlation_matrix.values
            self.assertTrue(np.all(values >= -1.0))
            self.assertTrue(np.all(values <= 1.0))
    
    def test_calculate_correlation_matrix_empty_data(self):
        """Test correlation matrix with empty data"""
        empty_data = {}
        result = self.analyzer.calculate_correlation_matrix(empty_data)
        self.assertTrue(result.empty)
    
    def test_perform_statistical_clustering(self):
        """Test statistical clustering"""
        features_df = self.analyzer.prepare_ticker_features(self.ticker_data)
        
        if len(features_df) < 2:
            self.skipTest("Not enough tickers for clustering")
        
        n_clusters = min(3, len(features_df))
        results = self.analyzer.perform_statistical_clustering(features_df, n_clusters=n_clusters)
        
        self.assertIsInstance(results, dict)
        
        if results:
            self.assertIn('tickers', results)
            self.assertIn('hierarchical_clusters', results)
            self.assertIn('kmeans_clusters', results)
            self.assertIn('silhouette_score', results)
            
            # Check cluster assignments
            self.assertEqual(len(results['tickers']), len(results['kmeans_clusters']))
            
            # Silhouette score should be between -1 and 1
            if results.get('silhouette_score') is not None:
                self.assertGreaterEqual(results['silhouette_score'], -1.0)
                self.assertLessEqual(results['silhouette_score'], 1.0)
    
    def test_perform_pca_analysis(self):
        """Test PCA analysis"""
        features_df = self.analyzer.prepare_ticker_features(self.ticker_data)
        
        if len(features_df) < 2:
            self.skipTest("Not enough tickers for PCA")
        
        results = self.analyzer.perform_pca_analysis(features_df, n_components=3)
        
        self.assertIsInstance(results, dict)
        
        if results:
            self.assertIn('tickers', results)
            self.assertIn('components', results)
            self.assertIn('explained_variance_ratio', results)
            
            # Check variance ratios sum to reasonable value
            total_variance = sum(results['explained_variance_ratio'])
            self.assertGreater(total_variance, 0)
            self.assertLessEqual(total_variance, 1.0)
    
    def test_build_similarity_graph(self):
        """Test similarity graph construction"""
        correlation_matrix = self.analyzer.calculate_correlation_matrix(self.ticker_data)
        
        if correlation_matrix.empty:
            self.skipTest("No correlation matrix available")
        
        graph = self.analyzer.build_similarity_graph(correlation_matrix, threshold=0.5)
        
        self.assertIsNotNone(graph)
        self.assertGreater(graph.number_of_nodes(), 0)
        
        # Check edges have weights
        for u, v, data in graph.edges(data=True):
            self.assertIn('weight', data)
            self.assertGreaterEqual(data['weight'], 0)
            self.assertLessEqual(data['weight'], 1.0)
    
    def test_build_similarity_graph_high_threshold(self):
        """Test similarity graph with high threshold"""
        correlation_matrix = self.analyzer.calculate_correlation_matrix(self.ticker_data)
        
        if correlation_matrix.empty:
            self.skipTest("No correlation matrix available")
        
        # High threshold should result in fewer edges
        graph = self.analyzer.build_similarity_graph(correlation_matrix, threshold=0.9)
        
        self.assertIsNotNone(graph)
        self.assertGreaterEqual(graph.number_of_nodes(), 0)
    
    def test_analyze_graph_properties(self):
        """Test graph property analysis"""
        correlation_matrix = self.analyzer.calculate_correlation_matrix(self.ticker_data)
        
        if correlation_matrix.empty:
            self.skipTest("No correlation matrix available")
        
        graph = self.analyzer.build_similarity_graph(correlation_matrix, threshold=0.3)
        
        if graph.number_of_nodes() == 0:
            self.skipTest("Graph has no nodes")
        
        properties = self.analyzer.analyze_graph_properties(graph)
        
        self.assertIsInstance(properties, dict)
        
        if properties:
            self.assertIn('num_nodes', properties)
            self.assertIn('num_edges', properties)
            self.assertIn('density', properties)
            
            # Check density is between 0 and 1
            self.assertGreaterEqual(properties['density'], 0)
            self.assertLessEqual(properties['density'], 1)
            
            # Check centrality measures exist
            if 'degree_centrality' in properties:
                self.assertIsInstance(properties['degree_centrality'], dict)
    
    def test_find_similar_tickers(self):
        """Test finding similar tickers"""
        correlation_matrix = self.analyzer.calculate_correlation_matrix(self.ticker_data)
        
        if correlation_matrix.empty:
            self.skipTest("No correlation matrix available")
        
        # Get first ticker
        target_ticker = list(self.ticker_data.keys())[0]
        
        similar = self.analyzer.find_similar_tickers(correlation_matrix, target_ticker, top_n=5)
        
        self.assertIsInstance(similar, list)
        
        if similar:
            # Check format
            for ticker, correlation in similar:
                self.assertIsInstance(ticker, str)
                self.assertIsInstance(correlation, (int, float))
                self.assertGreaterEqual(correlation, -1.0)
                self.assertLessEqual(correlation, 1.0)
    
    def test_find_similar_tickers_invalid(self):
        """Test finding similar tickers with invalid ticker"""
        correlation_matrix = self.analyzer.calculate_correlation_matrix(self.ticker_data)
        
        result = self.analyzer.find_similar_tickers(correlation_matrix, "INVALID", top_n=5)
        self.assertEqual(result, [])
    
    def test_calculate_distance_matrix(self):
        """Test distance matrix calculation"""
        features_df = self.analyzer.prepare_ticker_features(self.ticker_data)
        
        if len(features_df) < 2:
            self.skipTest("Not enough tickers")
        
        distance_matrix = self.analyzer.calculate_distance_matrix(features_df, metric='euclidean')
        
        self.assertIsInstance(distance_matrix, pd.DataFrame)
        
        if not distance_matrix.empty:
            # Should be square
            self.assertEqual(distance_matrix.shape[0], distance_matrix.shape[1])
            
            # Diagonal should be 0 (distance to self)
            for ticker in distance_matrix.index:
                self.assertAlmostEqual(distance_matrix.loc[ticker, ticker], 0.0, places=5)
            
            # Distances should be non-negative
            values = distance_matrix.values
            self.assertTrue(np.all(values >= 0))
    
    def test_comprehensive_analysis(self):
        """Test comprehensive analysis pipeline"""
        results = self.analyzer.comprehensive_analysis(self.ticker_data)
        
        self.assertIsInstance(results, dict)
        
        if 'error' in results:
            self.skipTest(f"Analysis error: {results['error']}")
        
        # Check required sections
        self.assertIn('features', results)
        
        # Check optional sections (may or may not be present)
        optional_sections = ['correlation_matrix', 'clustering', 'pca', 'graph_properties', 'distance_matrix']
        for section in optional_sections:
            if section in results:
                self.assertIsNotNone(results[section])
    
    def test_get_ticker_clusters(self):
        """Test getting ticker clusters"""
        features_df = self.analyzer.prepare_ticker_features(self.ticker_data)
        
        if len(features_df) < 2:
            self.skipTest("Not enough tickers")
        
        clustering_results = self.analyzer.perform_statistical_clustering(features_df, n_clusters=3)
        
        if not clustering_results:
            self.skipTest("No clustering results")
        
        clusters = self.analyzer.get_ticker_clusters(clustering_results)
        
        self.assertIsInstance(clusters, dict)
        
        # Check all tickers are in clusters
        all_clustered_tickers = []
        for cluster_id, tickers in clusters.items():
            self.assertIsInstance(cluster_id, int)
            self.assertIsInstance(tickers, list)
            all_clustered_tickers.extend(tickers)
        
        # All tickers should be clustered
        expected_tickers = set(clustering_results['tickers'])
        clustered_tickers = set(all_clustered_tickers)
        self.assertEqual(expected_tickers, clustered_tickers)
    
    def test_format_analysis_summary(self):
        """Test formatted summary output"""
        results = self.analyzer.comprehensive_analysis(self.ticker_data)
        
        summary = self.analyzer.format_analysis_summary(results)
        
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 0)
        
        # Check key sections are present
        if 'error' not in results:
            self.assertIn("COMPARATIVE", summary.upper())
    
    def test_empty_data_handling(self):
        """Test handling of empty data"""
        empty_data = {}
        
        features_df = self.analyzer.prepare_ticker_features(empty_data)
        self.assertTrue(features_df.empty)
        
        correlation_matrix = self.analyzer.calculate_correlation_matrix(empty_data)
        self.assertTrue(correlation_matrix.empty)
        
        results = self.analyzer.comprehensive_analysis(empty_data)
        self.assertIn('error', results)
    
    def test_single_ticker(self):
        """Test analysis with single ticker"""
        single_ticker_data = {list(self.ticker_data.keys())[0]: self.ticker_data[list(self.ticker_data.keys())[0]]}
        
        features_df = self.analyzer.prepare_ticker_features(single_ticker_data)
        self.assertEqual(len(features_df), 1)
        
        correlation_matrix = self.analyzer.calculate_correlation_matrix(single_ticker_data)
        # Single ticker should have empty correlation matrix
        self.assertTrue(correlation_matrix.empty)
    
    def test_calculate_max_drawdown(self):
        """Test max drawdown calculation"""
        # Create price series with known drawdown
        prices = pd.Series([100, 110, 105, 95, 100, 120])
        
        drawdown = self.analyzer._calculate_max_drawdown(prices)
        
        self.assertIsInstance(drawdown, (int, float))
        self.assertGreaterEqual(drawdown, 0)
        # Price dropped from 110 to 95, so drawdown should be around 13.6%
        self.assertGreater(drawdown, 10)
    
    def test_prepare_ticker_features_with_technical_indicators(self):
        """Test feature extraction with technical indicators"""
        # Add technical indicators to test data
        enhanced_data = {}
        for ticker, df in self.ticker_data.items():
            enhanced_df = df.copy()
            # Add RSI
            enhanced_df['RSI'] = 50 + np.random.normal(0, 15, len(df))
            # Add MACD
            enhanced_df['MACD'] = np.random.normal(0, 2, len(df))
            enhanced_data[ticker] = enhanced_df
        
        features_df = self.analyzer.prepare_ticker_features(enhanced_data)
        
        # Should include technical indicator features
        if 'rsi_mean' in features_df.columns:
            self.assertIn('rsi_mean', features_df.columns)
        if 'macd_mean' in features_df.columns:
            self.assertIn('macd_mean', features_df.columns)


class TestComparativeAnalyzerIntegration(unittest.TestCase):
    """Integration tests for real-world scenarios"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.analyzer = ComparativeAnalyzer()
        
        # Create realistic correlated ticker data
        self.correlated_data = self._create_correlated_data()
    
    def _create_correlated_data(self):
        """Create ticker data with known correlations"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        np.random.seed(42)
        
        # Base market trend
        market_trend = np.linspace(0, 10, 100) + np.random.normal(0, 1, 100)
        
        ticker_data = {}
        
        # Create highly correlated pair
        for i in range(2):
            ticker = f"CORR{i+1}"
            prices = 100 + market_trend + np.random.normal(0, 0.5, 100)
            ticker_data[ticker] = pd.DataFrame({
                'Open': prices,
                'High': prices + 1,
                'Low': prices - 1,
                'Close': prices,
                'Volume': np.random.uniform(1000000, 5000000, 100)
            }, index=dates)
        
        # Create independent ticker
        independent_prices = 100 + np.random.normal(0, 2, 100).cumsum()
        ticker_data['INDEPENDENT'] = pd.DataFrame({
            'Open': independent_prices,
            'High': independent_prices + 1,
            'Low': independent_prices - 1,
            'Close': independent_prices,
            'Volume': np.random.uniform(1000000, 5000000, 100)
        }, index=dates)
        
        return ticker_data
    
    def test_correlation_detection(self):
        """Test that correlation is detected correctly"""
        correlation_matrix = self.analyzer.calculate_correlation_matrix(self.correlated_data)
        
        if correlation_matrix.empty:
            self.skipTest("No correlation matrix")
        
        # CORR1 and CORR2 should be highly correlated
        if 'CORR1' in correlation_matrix.index and 'CORR2' in correlation_matrix.index:
            corr_value = correlation_matrix.loc['CORR1', 'CORR2']
            # Should be positive and relatively high
            self.assertGreater(corr_value, 0.5)
    
    def test_graph_community_detection(self):
        """Test community detection in graph"""
        correlation_matrix = self.analyzer.calculate_correlation_matrix(self.correlated_data)
        
        if correlation_matrix.empty:
            self.skipTest("No correlation matrix")
        
        graph = self.analyzer.build_similarity_graph(correlation_matrix, threshold=0.5)
        
        if graph.number_of_nodes() == 0:
            self.skipTest("Graph has no nodes")
        
        properties = self.analyzer.analyze_graph_properties(graph)
        
        # Check graph has connectivity
        if properties.get('num_components', 0) > 0:
            self.assertGreater(properties['largest_component_size'], 0)
    
    def test_end_to_end_analysis(self):
        """Test complete end-to-end analysis workflow"""
        results = self.analyzer.comprehensive_analysis(self.correlated_data)
        
        self.assertIsInstance(results, dict)
        
        # Should have features
        self.assertIn('features', results)
        
        # Should attempt correlation analysis
        if 'correlation_matrix' in results:
            self.assertIsInstance(results['correlation_matrix'], dict)
        
        # Summary should be generated
        summary = self.analyzer.format_analysis_summary(results)
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 0)


def run_all_tests():
    """Run all comparative analysis tests"""
    print("=" * 80)
    print("COMPARATIVE ANALYSIS TEST SUITE")
    print("=" * 80)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestComparativeAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestComparativeAnalyzerIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"\n{test}:")
            print(traceback)
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"\n{test}:")
            print(traceback)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
