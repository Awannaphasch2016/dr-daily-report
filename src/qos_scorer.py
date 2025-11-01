"""
QoS Scorer for System Performance Metrics

Measures Quality of Service (QoS) metrics including latency, cost, determinism,
reliability, resource efficiency, and scalability.
"""

import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class QoSScore:
    """Container for QoS scoring results"""
    overall_score: float  # 0-100
    dimension_scores: Dict[str, float]  # Individual dimension scores
    metrics: Dict[str, any]  # Raw metrics data
    issues: List[str]  # List of QoS issues
    strengths: List[str]  # List of QoS strengths
    timestamp: datetime = field(default_factory=datetime.now)


class QoSScorer:
    """
    Score Quality of Service (QoS) metrics for report generation
    
    Dimensions:
    1. Latency - Performance timing metrics
    2. Determinism - Consistency of deterministic components
    3. Reliability - Success/error rates
    4. Resource Efficiency - Database, memory, API call efficiency
    5. Scalability - Performance under load
    
    Note: Cost is tracked separately by CostScorer.
    """
    
    # Latency thresholds (in seconds)
    LATENCY_THRESHOLDS = {
        'excellent': 5.0,      # < 5s
        'good': 10.0,           # 5-10s
        'acceptable': 20.0,     # 10-20s
        'poor': float('inf')    # > 20s
    }
    
    def __init__(self):
        """Initialize QoS scorer"""
        pass
    
    def score_qos(
        self,
        timing_metrics: Dict[str, float],
        database_metrics: Dict[str, any],
        error_occurred: bool = False,
        cache_hit: bool = False,
        llm_calls: int = 0,
        historical_data: Optional[Dict] = None
    ) -> QoSScore:
        """
        Score QoS metrics
        
        Args:
            timing_metrics: Dict with timing data (e.g., {'data_fetch': 1.2, 'total': 8.5})
            database_metrics: Dict with DB metrics (e.g., {'query_count': 5, 'cache_hit': True})
            error_occurred: Whether an error occurred during execution
            cache_hit: Whether cached data was used
            llm_calls: Number of LLM API calls made
            historical_data: Optional historical QoS data for trend analysis
        
        Returns:
            QoSScore object with detailed scoring
        """
        issues = []
        strengths = []
        
        # 1. Score latency
        latency_score, latency_issues, latency_strengths = self._score_latency(
            timing_metrics, cache_hit
        )
        issues.extend(latency_issues)
        strengths.extend(latency_strengths)
        
        # 2. Score determinism (only for deterministic components)
        determinism_score, determinism_issues, determinism_strengths = self._score_determinism(
            timing_metrics, database_metrics, historical_data
        )
        issues.extend(determinism_issues)
        strengths.extend(determinism_strengths)
        
        # 3. Score reliability
        reliability_score, reliability_issues, reliability_strengths = self._score_reliability(
            error_occurred, cache_hit, timing_metrics
        )
        issues.extend(reliability_issues)
        strengths.extend(reliability_strengths)
        
        # 4. Score resource efficiency
        resource_score, resource_issues, resource_strengths = self._score_resource_efficiency(
            database_metrics, llm_calls, cache_hit
        )
        issues.extend(resource_issues)
        strengths.extend(resource_strengths)
        
        # 5. Score scalability (limited without load testing, but can infer from latency)
        scalability_score, scalability_issues, scalability_strengths = self._score_scalability(
            timing_metrics, historical_data
        )
        issues.extend(scalability_issues)
        strengths.extend(scalability_strengths)
        
        # Calculate overall score (weighted average)
        dimension_scores = {
            'latency': latency_score,
            'determinism': determinism_score,
            'reliability': reliability_score,
            'resource_efficiency': resource_score,
            'scalability': scalability_score
        }
        
        overall_score = (
            latency_score * 0.30 +
            determinism_score * 0.20 +
            reliability_score * 0.25 +
            resource_score * 0.15 +
            scalability_score * 0.10
        )
        
        # Combine all metrics (excluding cost - handled separately)
        metrics = {
            'timing': timing_metrics,
            'database': database_metrics,
            'error_occurred': error_occurred,
            'cache_hit': cache_hit,
            'llm_calls': llm_calls
        }
        
        return QoSScore(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            metrics=metrics,
            issues=issues,
            strengths=strengths
        )
    
    def _score_latency(
        self,
        timing_metrics: Dict[str, float],
        cache_hit: bool
    ) -> Tuple[float, List[str], List[str]]:
        """Score latency performance"""
        total_latency = timing_metrics.get('total', 0)
        issues = []
        strengths = []
        
        # Score based on total latency
        if total_latency < self.LATENCY_THRESHOLDS['excellent']:
            score = 100
            strengths.append(f"✅ Excellent total latency: {total_latency:.2f}s")
        elif total_latency < self.LATENCY_THRESHOLDS['good']:
            score = 85
            strengths.append(f"✅ Good total latency: {total_latency:.2f}s")
        elif total_latency < self.LATENCY_THRESHOLDS['acceptable']:
            score = 70
            issues.append(f"⚠️  Acceptable latency: {total_latency:.2f}s (target: <10s)")
        else:
            score = 50
            issues.append(f"❌ Poor latency: {total_latency:.2f}s (target: <10s)")
        
        # Check individual component latencies
        component_thresholds = {
            'data_fetch': 2.0,
            'news_fetch': 3.0,
            'technical_analysis': 2.0,
            'chart_generation': 3.0,
            'llm_generation': 5.0,
            'scoring': 1.0
        }
        
        for component, threshold in component_thresholds.items():
            if component in timing_metrics:
                comp_time = timing_metrics[component]
                if comp_time > threshold:
                    issues.append(f"⚠️  {component} latency high: {comp_time:.2f}s (target: <{threshold}s)")
        
        # Cache hit bonus
        if cache_hit:
            strengths.append("✅ Cache hit reduced latency")
        
        return score, issues, strengths
    
    def _score_determinism(
        self,
        timing_metrics: Dict[str, float],
        database_metrics: Dict[str, any],
        historical_data: Optional[Dict]
    ) -> Tuple[float, List[str], List[str]]:
        """
        Score determinism for deterministic components only
        
        Note: LLM output variance is NOT penalized (temperature is intentional)
        """
        issues = []
        strengths = []
        
        # Deterministic components should have consistent timing
        # Check if data fetch and technical analysis times are consistent
        data_fetch_time = timing_metrics.get('data_fetch', 0)
        tech_analysis_time = timing_metrics.get('technical_analysis', 0)
        
        # Base score (assume deterministic if no historical data)
        score = 90
        strengths.append("✅ Deterministic components (data fetch, calculations) executed")
        
        # If historical data available, check consistency
        if historical_data:
            hist_timing = historical_data.get('timing', {})
            if hist_timing:
                hist_data_fetch = hist_timing.get('data_fetch', 0)
                hist_tech_analysis = hist_timing.get('technical_analysis', 0)
                
                # Check variance (should be < 20% for deterministic components)
                if hist_data_fetch > 0:
                    variance = abs(data_fetch_time - hist_data_fetch) / hist_data_fetch
                    if variance > 0.2:
                        issues.append(f"⚠️  Data fetch timing variance: {variance*100:.1f}%")
                        score -= 10
                    else:
                        strengths.append("✅ Data fetch timing consistent")
                
                if hist_tech_analysis > 0:
                    variance = abs(tech_analysis_time - hist_tech_analysis) / hist_tech_analysis
                    if variance > 0.2:
                        issues.append(f"⚠️  Technical analysis timing variance: {variance*100:.1f}%")
                        score -= 10
                    else:
                        strengths.append("✅ Technical analysis timing consistent")
        
        # Database operations should be deterministic
        if database_metrics.get('query_count', 0) > 0:
            strengths.append(f"✅ Database queries executed consistently ({database_metrics['query_count']} queries)")
        
        return max(score, 50), issues, strengths
    
    def _score_reliability(
        self,
        error_occurred: bool,
        cache_hit: bool,
        timing_metrics: Dict[str, float]
    ) -> Tuple[float, List[str], List[str]]:
        """Score reliability/availability"""
        issues = []
        strengths = []
        
        # Error handling
        if error_occurred:
            score = 30
            issues.append("❌ Error occurred during execution")
        else:
            score = 100
            strengths.append("✅ No errors during execution")
        
        # Check for timeouts (very high latency might indicate timeout)
        total_latency = timing_metrics.get('total', 0)
        if total_latency > 60:
            score -= 20
            issues.append(f"⚠️  Very high latency ({total_latency:.2f}s) may indicate timeout")
        
        # Partial success handling (chart generation can fail but continue)
        chart_time = timing_metrics.get('chart_generation', 0)
        if chart_time == 0 and not error_occurred:
            strengths.append("✅ Graceful degradation (optional components handled)")
        
        return max(score, 0), issues, strengths
    
    def _score_resource_efficiency(
        self,
        database_metrics: Dict[str, any],
        llm_calls: int,
        cache_hit: bool
    ) -> Tuple[float, List[str], List[str]]:
        """Score resource efficiency"""
        issues = []
        strengths = []
        
        score = 100
        
        # Database query efficiency
        query_count = database_metrics.get('query_count', 0)
        if query_count > 10:
            score -= 15
            issues.append(f"⚠️  High database query count: {query_count} (target: <10)")
        elif query_count > 5:
            score -= 5
            issues.append(f"⚠️  Moderate database query count: {query_count}")
        else:
            strengths.append(f"✅ Efficient database usage: {query_count} queries")
        
        # LLM call efficiency
        if llm_calls > 2:
            score -= 10
            issues.append(f"⚠️  Multiple LLM calls: {llm_calls} (target: ≤2)")
        elif llm_calls == 1:
            strengths.append("✅ Single LLM call optimized")
        
        # Cache utilization
        if cache_hit:
            strengths.append("✅ Cache utilization improved efficiency")
        else:
            # Not penalizing, but noting optimization opportunity
            pass
        
        return max(score, 50), issues, strengths
    
    def _score_scalability(
        self,
        timing_metrics: Dict[str, float],
        historical_data: Optional[Dict]
    ) -> Tuple[float, List[str], List[str]]:
        """
        Score scalability (limited without load testing)
        
        Infer from latency trends and component performance
        """
        issues = []
        strengths = []
        
        # Base score (assume good scalability if latency is reasonable)
        total_latency = timing_metrics.get('total', 0)
        
        if total_latency < self.LATENCY_THRESHOLDS['good']:
            score = 90
            strengths.append("✅ Low latency suggests good scalability")
        elif total_latency < self.LATENCY_THRESHOLDS['acceptable']:
            score = 75
            issues.append("⚠️  Moderate latency may impact scalability under load")
        else:
            score = 60
            issues.append("⚠️  High latency may limit scalability")
        
        # Check if latency is trending up (from historical data)
        if historical_data:
            hist_timing = historical_data.get('timing', {})
            if hist_timing:
                hist_total = hist_timing.get('total', 0)
                if hist_total > 0:
                    latency_increase = (total_latency - hist_total) / hist_total
                    if latency_increase > 0.2:
                        score -= 15
                        issues.append(f"⚠️  Latency increased {latency_increase*100:.1f}% from historical baseline")
                    elif latency_increase < -0.1:
                        strengths.append(f"✅ Latency improved {abs(latency_increase)*100:.1f}% from baseline")
        
        return max(score, 50), issues, strengths
    
    def format_score_report(self, score: QoSScore) -> str:
        """Format human-readable QoS score report"""
        report = "\n" + "="*70 + "\n"
        report += "QoS SCORE REPORT\n"
        report += "="*70 + "\n"
        report += f"Overall QoS Score: {score.overall_score:.1f}/100\n\n"
        
        report += "Dimension Scores:\n"
        report += "-" * 70 + "\n"
        for dimension, dim_score in score.dimension_scores.items():
            dimension_name = dimension.replace('_', ' ').title()
            grade = self._get_score_grade(dim_score)
            report += f"  {dimension_name:25s}: {dim_score:5.1f}/100 {grade}\n"
        
        report += "\n" + "-" * 70 + "\n"
        report += "Metrics:\n"
        report += "-" * 70 + "\n"
        
        # Timing metrics
        timing = score.metrics.get('timing', {})
        report += "  Timing (seconds):\n"
        for component, time_val in timing.items():
            report += f"    {component:25s}: {time_val:6.2f}s\n"
        
        # Database metrics
        db_metrics = score.metrics.get('database', {})
        report += "\n  Database:\n"
        report += f"    Query Count:            {db_metrics.get('query_count', 0)}\n"
        report += f"    Cache Hit:              {'Yes' if db_metrics.get('cache_hit') else 'No'}\n"
        
        # Other metrics
        report += "\n  Other:\n"
        report += f"    LLM Calls:              {score.metrics.get('llm_calls', 0)}\n"
        report += f"    Error Occurred:         {'Yes' if score.metrics.get('error_occurred') else 'No'}\n"
        
        report += "\n  Note: Cost is tracked separately by CostScorer\n"
        
        if score.strengths:
            report += "\n" + "-" * 70 + "\n"
            report += "Strengths:\n"
            for strength in score.strengths:
                report += f"  {strength}\n"
        
        if score.issues:
            report += "\n" + "-" * 70 + "\n"
            report += "Issues:\n"
            for issue in score.issues:
                report += f"  {issue}\n"
        
        report += "\n" + "="*70 + "\n"
        return report
    
    def _get_score_grade(self, score: float) -> str:
        """Get grade for score"""
        if score >= 90:
            return "(Excellent)"
        elif score >= 80:
            return "(Good)"
        elif score >= 70:
            return "(Acceptable)"
        elif score >= 60:
            return "(Needs Improvement)"
        else:
            return "(Poor)"
