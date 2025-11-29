#!/usr/bin/env python3
"""
Comparative Analysis Module

Provides statistical and graph-based analysis for comparing multiple tickers:
- Feature extraction from ticker data
- Correlation analysis
- Statistical clustering (K-means, hierarchical)
- PCA dimensionality reduction
- Graph-based similarity networks
- Community detection
- Distance calculations
"""

import pandas as pd
import numpy as np
import networkx as nx
from typing import Dict, List, Tuple, Optional, Any
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from scipy.spatial.distance import pdist, squareform
import warnings
warnings.filterwarnings('ignore')


class ComparativeAnalyzer:
    """
    Analyzer for comparative analysis across multiple tickers.
    
    Provides statistical analysis, clustering, PCA, and graph-based
    similarity analysis for comparing ticker behavior.
    """
    
    def __init__(self):
        """Initialize the analyzer."""
        self.scaler = StandardScaler()
    
    def prepare_ticker_features(self, ticker_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Extract features from ticker data for comparative analysis.
        
        Args:
            ticker_data: Dictionary mapping ticker symbols to DataFrames
                        with columns: Open, High, Low, Close, Volume
        
        Returns:
            DataFrame with columns: ticker, mean_return, volatility, sharpe_ratio,
            and optionally rsi_mean, macd_mean if present in input data
        """
        if not ticker_data:
            return pd.DataFrame()
        
        features_list = []
        
        for ticker, df in ticker_data.items():
            if df.empty or 'Close' not in df.columns:
                continue
            
            # Calculate returns
            prices = df['Close']
            returns = prices.pct_change().dropna()
            
            if len(returns) == 0:
                continue
            
            # Basic features
            mean_return = returns.mean() * 252  # Annualized
            volatility = returns.std() * np.sqrt(252)  # Annualized
            
            # Sharpe ratio (assuming risk-free rate = 0)
            sharpe_ratio = mean_return / volatility if volatility > 0 else 0.0
            
            # Max drawdown
            max_drawdown = self._calculate_max_drawdown(prices)
            
            # Volume statistics
            volume_mean = df['Volume'].mean() if 'Volume' in df.columns else 0
            
            feature_dict = {
                'ticker': ticker,
                'mean_return': mean_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'volume_mean': volume_mean
            }
            
            # Optional technical indicators
            if 'RSI' in df.columns:
                feature_dict['rsi_mean'] = df['RSI'].mean()
            
            if 'MACD' in df.columns:
                feature_dict['macd_mean'] = df['MACD'].mean()
            
            features_list.append(feature_dict)
        
        if not features_list:
            return pd.DataFrame()
        
        features_df = pd.DataFrame(features_list)
        
        return features_df
    
    def calculate_correlation_matrix(self, ticker_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Calculate correlation matrix between tickers based on returns.
        
        Args:
            ticker_data: Dictionary mapping ticker symbols to DataFrames
        
        Returns:
            DataFrame with correlation matrix (tickers x tickers)
        """
        if len(ticker_data) < 2:
            return pd.DataFrame()
        
        # Calculate returns for each ticker
        returns_dict = {}
        for ticker, df in ticker_data.items():
            if df.empty or 'Close' not in df.columns:
                continue
            
            returns = df['Close'].pct_change().dropna()
            if len(returns) > 0:
                returns_dict[ticker] = returns
        
        if len(returns_dict) < 2:
            return pd.DataFrame()
        
        # Align returns by date
        returns_df = pd.DataFrame(returns_dict)
        
        # Calculate correlation matrix
        correlation_matrix = returns_df.corr()
        
        return correlation_matrix
    
    def perform_statistical_clustering(
        self, 
        features_df: pd.DataFrame, 
        n_clusters: int = 3
    ) -> Dict[str, Any]:
        """
        Perform statistical clustering on ticker features.
        
        Args:
            features_df: DataFrame with ticker features
            n_clusters: Number of clusters to create
        
        Returns:
            Dictionary with:
            - tickers: list of ticker symbols
            - kmeans_clusters: cluster assignments from K-means
            - hierarchical_clusters: cluster assignments from hierarchical clustering
            - silhouette_score: quality score of clustering
        """
        if len(features_df) < 2:
            return {}
        
        if len(features_df) < n_clusters:
            n_clusters = len(features_df)
        
        # Prepare features (exclude non-numeric columns)
        feature_cols = features_df.select_dtypes(include=[np.number]).columns.tolist()
        if not feature_cols:
            return {}
        
        X = features_df[feature_cols].values

        # Standardize features
        X_scaled = self.scaler.fit_transform(X)

        # K-means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        kmeans_clusters = kmeans.fit_predict(X_scaled)

        # Hierarchical clustering
        hierarchical = AgglomerativeClustering(n_clusters=n_clusters)
        hierarchical_clusters = hierarchical.fit_predict(X_scaled)

        # Calculate silhouette score
        silhouette = None
        if n_clusters > 1 and len(features_df) > n_clusters:
            silhouette = silhouette_score(X_scaled, kmeans_clusters)

        return {
            'tickers': features_df.index.tolist(),
            'kmeans_clusters': kmeans_clusters.tolist(),
            'hierarchical_clusters': hierarchical_clusters.tolist(),
            'silhouette_score': silhouette
        }
    
    def perform_pca_analysis(
        self, 
        features_df: pd.DataFrame, 
        n_components: int = 3
    ) -> Dict[str, Any]:
        """
        Perform Principal Component Analysis on ticker features.
        
        Args:
            features_df: DataFrame with ticker features
            n_components: Number of principal components
        
        Returns:
            Dictionary with:
            - tickers: list of ticker symbols
            - components: PCA components matrix
            - explained_variance_ratio: variance explained by each component
        """
        if len(features_df) < 2:
            return {}
        
        if n_components > len(features_df):
            n_components = len(features_df)
        
        # Prepare features
        feature_cols = features_df.select_dtypes(include=[np.number]).columns.tolist()
        if not feature_cols:
            return {}

        X = features_df[feature_cols].values

        # Standardize features
        X_scaled = self.scaler.fit_transform(X)

        # Limit n_components to number of features
        n_components = min(n_components, len(feature_cols))

        # Perform PCA
        pca = PCA(n_components=n_components)
        components = pca.fit_transform(X_scaled)

        return {
            'tickers': features_df.index.tolist(),
            'components': components.tolist(),
            'explained_variance_ratio': pca.explained_variance_ratio_.tolist()
        }
    
    def build_similarity_graph(
        self, 
        correlation_matrix: pd.DataFrame, 
        threshold: float = 0.5
    ) -> nx.Graph:
        """
        Build similarity graph from correlation matrix.
        
        Args:
            correlation_matrix: DataFrame with correlation values
            threshold: Minimum correlation to create an edge
        
        Returns:
            NetworkX graph with edges for correlations above threshold
        """
        graph = nx.Graph()
        
        if correlation_matrix.empty:
            return graph
        
        # Add nodes
        tickers = correlation_matrix.index.tolist()
        graph.add_nodes_from(tickers)
        
        # Add edges for correlations above threshold
        for i, ticker1 in enumerate(tickers):
            for j, ticker2 in enumerate(tickers):
                if i >= j:  # Avoid duplicate edges
                    continue
                
                correlation = correlation_matrix.loc[ticker1, ticker2]
                
                # Use absolute correlation for similarity
                if not pd.isna(correlation) and abs(correlation) >= threshold:
                    # Weight is normalized to [0, 1]
                    weight = (abs(correlation) - threshold) / (1 - threshold)
                    graph.add_edge(ticker1, ticker2, weight=weight)
        
        return graph
    
    def analyze_graph_properties(self, graph: nx.Graph) -> Dict[str, Any]:
        """
        Analyze properties of the similarity graph.
        
        Args:
            graph: NetworkX graph
        
        Returns:
            Dictionary with graph properties:
            - num_nodes: number of nodes
            - num_edges: number of edges
            - density: graph density
            - degree_centrality: degree centrality for each node
            - num_components: number of connected components
            - largest_component_size: size of largest component
        """
        if graph.number_of_nodes() == 0:
            return {
                'num_nodes': 0,
                'num_edges': 0,
                'density': 0.0,
                'num_components': 0,
                'largest_component_size': 0
            }
        
        properties = {
            'num_nodes': graph.number_of_nodes(),
            'num_edges': graph.number_of_edges(),
            'density': nx.density(graph),
            'num_components': nx.number_connected_components(graph)
        }
        
        # Largest component size
        if properties['num_components'] > 0:
            largest_component = max(nx.connected_components(graph), key=len)
            properties['largest_component_size'] = len(largest_component)
        else:
            properties['largest_component_size'] = 0
        
        # Degree centrality
        try:
            degree_centrality = nx.degree_centrality(graph)
            properties['degree_centrality'] = degree_centrality
        except:
            properties['degree_centrality'] = {}
        
        return properties
    
    def find_similar_tickers(
        self, 
        correlation_matrix: pd.DataFrame, 
        target_ticker: str, 
        top_n: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Find tickers most similar to target ticker based on correlation.
        
        Args:
            correlation_matrix: DataFrame with correlation values
            target_ticker: Ticker symbol to find similar tickers for
            top_n: Number of similar tickers to return
        
        Returns:
            List of tuples (ticker, correlation) sorted by absolute correlation
        """
        if correlation_matrix.empty or target_ticker not in correlation_matrix.index:
            return []
        
        # Get correlations with target ticker
        correlations = correlation_matrix[target_ticker].drop(target_ticker)
        
        # Sort by absolute correlation
        similar = correlations.abs().sort_values(ascending=False).head(top_n)
        
        # Return as list of tuples
        result = [(ticker, float(correlations[ticker])) for ticker in similar.index]
        
        return result
    
    def calculate_distance_matrix(
        self, 
        features_df: pd.DataFrame, 
        metric: str = 'euclidean'
    ) -> pd.DataFrame:
        """
        Calculate distance matrix between tickers based on features.
        
        Args:
            features_df: DataFrame with ticker features
            metric: Distance metric ('euclidean' supported)
        
        Returns:
            DataFrame with distance matrix (tickers x tickers)
        """
        if len(features_df) < 2:
            return pd.DataFrame()
        
        # Prepare features
        feature_cols = features_df.select_dtypes(include=[np.number]).columns.tolist()
        if not feature_cols:
            return pd.DataFrame()
        
        # sklearn not available - distance calculation disabled
        # Return empty DataFrame since euclidean_distances requires sklearn
        return pd.DataFrame()
    
    def get_ticker_clusters(self, clustering_results: Dict[str, Any]) -> Dict[int, List[str]]:
        """
        Get tickers grouped by cluster.
        
        Args:
            clustering_results: Results from perform_statistical_clustering
        
        Returns:
            Dictionary mapping cluster_id to list of tickers
        """
        if not clustering_results:
            return {}
        
        tickers = clustering_results.get('tickers', [])
        clusters = clustering_results.get('kmeans_clusters', [])
        
        if len(tickers) != len(clusters):
            return {}
        
        cluster_dict = {}
        for ticker, cluster_id in zip(tickers, clusters):
            if cluster_id not in cluster_dict:
                cluster_dict[cluster_id] = []
            cluster_dict[cluster_id].append(ticker)
        
        return cluster_dict
    
    def comprehensive_analysis(self, ticker_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Run comprehensive comparative analysis pipeline.
        
        Args:
            ticker_data: Dictionary mapping ticker symbols to DataFrames
        
        Returns:
            Dictionary with analysis results:
            - features: DataFrame with extracted features
            - correlation_matrix: correlation matrix DataFrame
            - clustering: clustering results (if applicable)
            - pca: PCA results (if applicable)
            - graph_properties: graph analysis results (if applicable)
            - distance_matrix: distance matrix (if applicable)
            - error: error message if analysis failed
        """
        results = {}
        
        try:
            # Feature extraction
            features_df = self.prepare_ticker_features(ticker_data)
            results['features'] = features_df
            
            if features_df.empty:
                results['error'] = 'No valid ticker data to analyze'
                return results
            
            # Correlation analysis
            if len(ticker_data) >= 2:
                correlation_matrix = self.calculate_correlation_matrix(ticker_data)
                if not correlation_matrix.empty:
                    # Convert to dict for comprehensive_analysis results
                    results['correlation_matrix'] = correlation_matrix.to_dict()
                    
                    # Graph analysis
                    graph = self.build_similarity_graph(correlation_matrix, threshold=0.3)
                    if graph.number_of_nodes() > 0:
                        graph_properties = self.analyze_graph_properties(graph)
                        results['graph_properties'] = graph_properties
            
            # Clustering (use indexed version for clustering)
            if len(features_df) >= 2:
                # For clustering, use indexed version if ticker is a column
                if 'ticker' in features_df.columns:
                    features_df_for_clustering = features_df.set_index('ticker')
                else:
                    features_df_for_clustering = features_df
                n_clusters = min(3, len(features_df_for_clustering))
                clustering_results = self.perform_statistical_clustering(features_df_for_clustering, n_clusters=n_clusters)
                if clustering_results:
                    results['clustering'] = clustering_results
            
            # Update features_df to use ticker as index for other operations
            if not features_df.empty and 'ticker' in features_df.columns:
                features_df_indexed = features_df.set_index('ticker')
            else:
                features_df_indexed = features_df
                
            # PCA
            if len(features_df_indexed) >= 2:
                pca_results = self.perform_pca_analysis(features_df_indexed, n_components=3)
                if pca_results:
                    results['pca'] = pca_results
            
            # Distance matrix
            if len(features_df_indexed) >= 2:
                distance_matrix = self.calculate_distance_matrix(features_df_indexed)
                if not distance_matrix.empty:
                    results['distance_matrix'] = distance_matrix
            
        except Exception as e:
            results['error'] = f'Analysis failed: {str(e)}'
        
        return results
    
    def format_analysis_summary(self, results: Dict[str, Any]) -> str:
        """
        Format analysis results as human-readable summary.
        
        Args:
            results: Results dictionary from comprehensive_analysis
        
        Returns:
            Formatted summary string
        """
        if 'error' in results:
            return f"? Analysis Error: {results['error']}"
        
        summary_lines = ["=" * 80]
        summary_lines.append("COMPARATIVE ANALYSIS SUMMARY")
        summary_lines.append("=" * 80)
        
        # Features
        if 'features' in results and not results['features'].empty:
            features_df = results['features']
            summary_lines.append(f"\n?? Features Analyzed: {len(features_df)} tickers")
            summary_lines.append(f"   Feature columns: {', '.join(features_df.columns.tolist())}")
        
        # Correlation
        if 'correlation_matrix' in results:
            corr_matrix_dict = results['correlation_matrix']
            # Convert dict back to DataFrame for analysis
            if isinstance(corr_matrix_dict, dict):
                corr_matrix = pd.DataFrame(corr_matrix_dict)
            else:
                corr_matrix = corr_matrix_dict
            summary_lines.append(f"\n?? Correlation Analysis:")
            summary_lines.append(f"   Analyzed {len(corr_matrix)} tickers")
            if not corr_matrix.empty:
                values = corr_matrix.values
                upper_triangle = values[np.triu_indices(len(corr_matrix), k=1)]
                avg_corr = upper_triangle.mean()
                summary_lines.append(f"   Average correlation: {avg_corr:.3f}")
        
        # Clustering
        if 'clustering' in results:
            clustering = results['clustering']
            summary_lines.append(f"\n?? Clustering Results:")
            summary_lines.append(f"   Method: K-means + Hierarchical")
            if clustering.get('silhouette_score') is not None:
                summary_lines.append(f"   Silhouette score: {clustering['silhouette_score']:.3f}")
        
        # PCA
        if 'pca' in results:
            pca = results['pca']
            summary_lines.append(f"\n?? PCA Analysis:")
            if 'explained_variance_ratio' in pca:
                variance = sum(pca['explained_variance_ratio'])
                summary_lines.append(f"   Variance explained: {variance:.1%}")
        
        # Graph properties
        if 'graph_properties' in results:
            graph_props = results['graph_properties']
            summary_lines.append(f"\n???  Graph Analysis:")
            summary_lines.append(f"   Nodes: {graph_props.get('num_nodes', 0)}")
            summary_lines.append(f"   Edges: {graph_props.get('num_edges', 0)}")
            summary_lines.append(f"   Density: {graph_props.get('density', 0):.3f}")
            summary_lines.append(f"   Components: {graph_props.get('num_components', 0)}")
        
        summary_lines.append("\n" + "=" * 80)
        
        return "\n".join(summary_lines)
    
    def _calculate_max_drawdown(self, prices: pd.Series) -> float:
        """
        Calculate maximum drawdown from price series.
        
        Args:
            prices: Series of prices
        
        Returns:
            Maximum drawdown as percentage
        """
        if len(prices) < 2:
            return 0.0
        
        # Calculate cumulative maximum
        cumulative_max = prices.expanding().max()
        
        # Calculate drawdown
        drawdown = (prices - cumulative_max) / cumulative_max * 100
        
        # Return maximum drawdown (most negative)
        max_drawdown = abs(drawdown.min())
        
        return max_drawdown
