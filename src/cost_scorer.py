"""
Cost Scorer for Report Generation

Measures the operational cost of generating a report in Thai Baht (THB).
Tracks API costs, database operations, and other resource costs.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CostScore:
    """Container for cost scoring results"""
    overall_cost_thb: float  # Total cost in Thai Baht
    cost_breakdown: Dict[str, float]  # Cost breakdown by component
    cost_efficiency_score: float  # 0-100 score based on cost efficiency
    token_usage: Dict[str, int]  # Token usage statistics
    llm_calls: int  # Number of LLM API calls
    issues: List[str]  # List of cost-related issues
    strengths: List[str]  # List of cost optimization strengths
    timestamp: datetime = field(default_factory=datetime.now)


class CostScorer:
    """
    Score operational costs for report generation
    
    Tracks:
    1. LLM API costs (OpenAI)
    2. Database operation costs
    3. External API costs (if applicable)
    """
    
    # GPT-4o pricing (as of 2024, update as needed)
    GPT4O_INPUT_RATE_USD = 2.50 / 1_000_000   # $2.50 per 1M input tokens
    GPT4O_OUTPUT_RATE_USD = 10.00 / 1_000_000  # $10.00 per 1M output tokens
    
    # USD to THB exchange rate (update as needed)
    # Using approximate rate: 1 USD ≈ 35 THB
    USD_TO_THB_RATE = 35.0
    
    # Cost efficiency thresholds (in THB)
    COST_THRESHOLDS = {
        'excellent': 1.75,      # < 1.75 THB (< $0.05)
        'good': 3.50,           # 1.75-3.50 THB ($0.05-0.10)
        'acceptable': 7.00,     # 3.50-7.00 THB ($0.10-0.20)
        'poor': float('inf')    # > 7.00 THB (> $0.20)
    }
    
    # Database operation cost (per query) - estimated
    DB_QUERY_COST_THB = 0.001  # 0.001 THB per query (negligible)
    
    def __init__(self):
        """Initialize cost scorer"""
        pass
    
    def score_cost(
        self,
        api_costs: Dict[str, float],
        llm_calls: int,
        database_metrics: Dict[str, any],
        cache_hit: bool = False
    ) -> CostScore:
        """
        Score operational costs
        
        Args:
            api_costs: Dict with API costs (e.g., {'llm_actual': 0.08, 'llm_estimated': 0.08})
            llm_calls: Number of LLM API calls made
            database_metrics: Dict with DB metrics (e.g., {'query_count': 5})
            cache_hit: Whether cached data was used
        
        Returns:
            CostScore object with detailed cost breakdown
        """
        issues = []
        strengths = []
        
        # Calculate LLM cost in THB
        llm_cost_usd = api_costs.get('llm_actual') or api_costs.get('llm_estimated', 0)
        llm_cost_thb = llm_cost_usd * self.USD_TO_THB_RATE
        
        # Calculate database cost
        db_query_count = database_metrics.get('query_count', 0)
        db_cost_thb = db_query_count * self.DB_QUERY_COST_THB
        
        # Total cost
        total_cost_thb = llm_cost_thb + db_cost_thb
        
        # Cost breakdown
        cost_breakdown = {
            'llm_cost_thb': llm_cost_thb,
            'db_cost_thb': db_cost_thb,
            'total_cost_thb': total_cost_thb,
            'llm_cost_usd': llm_cost_usd,
            'db_query_count': db_query_count
        }
        
        # Token usage
        token_usage = {
            'input_tokens': api_costs.get('input_tokens', 0),
            'output_tokens': api_costs.get('output_tokens', 0),
            'total_tokens': api_costs.get('input_tokens', 0) + api_costs.get('output_tokens', 0)
        }
        
        # Score cost efficiency (lower is better)
        if total_cost_thb < self.COST_THRESHOLDS['excellent']:
            cost_efficiency_score = 100
            strengths.append(f"✅ Excellent cost efficiency: {total_cost_thb:.4f} THB")
        elif total_cost_thb < self.COST_THRESHOLDS['good']:
            cost_efficiency_score = 85
            strengths.append(f"✅ Good cost efficiency: {total_cost_thb:.4f} THB")
        elif total_cost_thb < self.COST_THRESHOLDS['acceptable']:
            cost_efficiency_score = 70
            issues.append(f"⚠️  Acceptable cost: {total_cost_thb:.4f} THB (target: <3.50 THB)")
        else:
            cost_efficiency_score = 50
            issues.append(f"❌ High cost: {total_cost_thb:.4f} THB (target: <3.50 THB)")
        
        # Check LLM call count
        if llm_calls > 2:
            issues.append(f"⚠️  Multiple LLM calls ({llm_calls}) increased cost")
            cost_efficiency_score -= 10
        elif llm_calls == 1:
            strengths.append("✅ Single LLM call optimized cost")
        
        # Cache hit bonus
        if cache_hit:
            strengths.append("✅ Cache hit reduced API costs")
        else:
            # Not penalizing, but noting optimization opportunity
            pass
        
        # Check token usage efficiency
        total_tokens = token_usage['total_tokens']
        if total_tokens > 10000:
            issues.append(f"⚠️  High token usage: {total_tokens:,} tokens")
        elif total_tokens < 3000:
            strengths.append(f"✅ Efficient token usage: {total_tokens:,} tokens")
        
        return CostScore(
            overall_cost_thb=total_cost_thb,
            cost_breakdown=cost_breakdown,
            cost_efficiency_score=max(cost_efficiency_score, 0),
            token_usage=token_usage,
            llm_calls=llm_calls,
            issues=issues,
            strengths=strengths
        )
    
    def calculate_api_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        actual_cost_usd: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate API cost in USD
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            actual_cost_usd: Actual cost from API response (if available)
        
        Returns:
            Dict with 'llm_actual' and 'llm_estimated' costs in USD
        """
        estimated_cost_usd = (
            input_tokens * self.GPT4O_INPUT_RATE_USD +
            output_tokens * self.GPT4O_OUTPUT_RATE_USD
        )
        
        return {
            'llm_actual': actual_cost_usd,
            'llm_estimated': estimated_cost_usd,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens
        }
    
    def format_score_report(self, score: CostScore) -> str:
        """Format human-readable cost score report"""
        report = "\n" + "="*70 + "\n"
        report += "COST SCORE REPORT\n"
        report += "="*70 + "\n"
        report += f"Total Cost: {score.overall_cost_thb:.4f} THB\n"
        report += f"Cost Efficiency Score: {score.cost_efficiency_score:.1f}/100\n\n"
        
        report += "Cost Breakdown:\n"
        report += "-" * 70 + "\n"
        report += f"  LLM API Cost:           {score.cost_breakdown['llm_cost_thb']:.4f} THB\n"
        report += f"  LLM API Cost (USD):     ${score.cost_breakdown['llm_cost_usd']:.6f}\n"
        report += f"  Database Cost:           {score.cost_breakdown['db_cost_thb']:.4f} THB\n"
        report += f"  Database Queries:       {score.cost_breakdown['db_query_count']}\n"
        report += f"  Total Cost:              {score.overall_cost_thb:.4f} THB\n"
        
        report += "\n" + "-" * 70 + "\n"
        report += "Token Usage:\n"
        report += "-" * 70 + "\n"
        report += f"  Input Tokens:           {score.token_usage['input_tokens']:,}\n"
        report += f"  Output Tokens:          {score.token_usage['output_tokens']:,}\n"
        report += f"  Total Tokens:           {score.token_usage['total_tokens']:,}\n"
        
        report += "\n" + "-" * 70 + "\n"
        report += "Operation Details:\n"
        report += "-" * 70 + "\n"
        report += f"  LLM API Calls:          {score.llm_calls}\n"
        
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
