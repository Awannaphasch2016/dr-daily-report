#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangSmith Evaluator Wrappers

Wraps existing 6 evaluation scorers to return LangSmith-compatible format.
Each evaluator returns: {key, score, comment}

Evaluators:
1. Faithfulness - Accuracy of LLM narratives
2. Completeness - Coverage of analytical dimensions
3. Reasoning Quality - Quality of explanations
4. Compliance - Format/policy adherence
5. QoS - System performance metrics
6. Cost - Operational costs
"""

from typing import Dict, Any


class LangSmithEvaluators:
    """Wrapper class for all LangSmith evaluators"""

    @staticmethod
    def faithfulness_evaluator(score_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangSmith evaluator for Faithfulness score.

        Args:
            score_data: Dictionary containing faithfulness score details
                - overall_score: Overall faithfulness score (0-100)
                - numeric_accuracy: Numeric accuracy component (0-100)
                - percentile_accuracy: Percentile accuracy component (0-100)
                - news_citation_accuracy: News citation accuracy (0-100)
                - interpretation_accuracy: Interpretation accuracy (0-100)
                - violations: List of faithfulness violations

        Returns:
            LangSmith-compatible dict with key, score, comment
        """
        overall_score = score_data.get('overall_score', 0)

        # Build detailed breakdown comment
        numeric = score_data.get('numeric_accuracy', 0)
        percentile = score_data.get('percentile_accuracy', 0)
        news = score_data.get('news_citation_accuracy', 0)
        interpretation = score_data.get('interpretation_accuracy', 0)

        violations = score_data.get('violations', [])
        violation_summary = f" | {len(violations)} violations" if violations else ""

        comment = (
            f"Numeric: {numeric:.1f}%, Percentile: {percentile:.1f}%, "
            f"News: {news:.1f}%, Interpretation: {interpretation:.1f}%{violation_summary}"
        )

        return {
            "key": "faithfulness_score",
            "score": overall_score / 100.0,  # Normalize to 0-1 for LangSmith
            "comment": comment
        }

    @staticmethod
    def completeness_evaluator(score_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangSmith evaluator for Completeness score.

        Args:
            score_data: Dictionary containing completeness score details
                - overall_score: Overall completeness score (0-100)
                - context_completeness: Context dimension (0-100)
                - analysis_dimensions: Analysis dimension (0-100)
                - temporal_completeness: Temporal dimension (0-100)
                - actionability: Actionability dimension (0-100)
                - narrative_structure: Structure dimension (0-100)
                - quantitative_context: Quantitative dimension (0-100)
                - missing_elements: List of missing elements

        Returns:
            LangSmith-compatible dict with key, score, comment
        """
        overall_score = score_data.get('overall_score', 0)

        # Build detailed breakdown comment
        context = score_data.get('context_completeness', 0)
        analysis = score_data.get('analysis_dimensions', 0)
        temporal = score_data.get('temporal_completeness', 0)
        actionability = score_data.get('actionability', 0)
        structure = score_data.get('narrative_structure', 0)
        quantitative = score_data.get('quantitative_context', 0)

        missing = score_data.get('missing_elements', [])
        missing_summary = f" | Missing: {len(missing)}" if missing else ""

        comment = (
            f"Context: {context:.1f}%, Analysis: {analysis:.1f}%, "
            f"Temporal: {temporal:.1f}%, Actionability: {actionability:.1f}%, "
            f"Structure: {structure:.1f}%, Quantitative: {quantitative:.1f}%{missing_summary}"
        )

        return {
            "key": "completeness_score",
            "score": overall_score / 100.0,
            "comment": comment
        }

    @staticmethod
    def reasoning_quality_evaluator(score_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangSmith evaluator for Reasoning Quality score.

        Args:
            score_data: Dictionary containing reasoning quality score details
                - overall_score: Overall reasoning quality score (0-100)
                - clarity: Clarity dimension (0-100)
                - coverage: Coverage dimension (0-100)
                - specificity: Specificity dimension (0-100)
                - alignment: Alignment dimension (0-100)
                - minimality: Minimality dimension (0-100)
                - consistency: Consistency dimension (0-100)
                - issues: List of quality issues
                - strengths: List of quality strengths

        Returns:
            LangSmith-compatible dict with key, score, comment
        """
        overall_score = score_data.get('overall_score', 0)

        # Build detailed breakdown comment
        clarity = score_data.get('clarity', 0)
        coverage = score_data.get('coverage', 0)
        specificity = score_data.get('specificity', 0)
        alignment = score_data.get('alignment', 0)
        minimality = score_data.get('minimality', 0)
        consistency = score_data.get('consistency', 0)

        issues = score_data.get('issues', [])
        strengths = score_data.get('strengths', [])

        quality_summary = f" | Issues: {len(issues)}, Strengths: {len(strengths)}"

        comment = (
            f"Clarity: {clarity:.1f}%, Coverage: {coverage:.1f}%, "
            f"Specificity: {specificity:.1f}%, Alignment: {alignment:.1f}%, "
            f"Minimality: {minimality:.1f}%, Consistency: {consistency:.1f}%{quality_summary}"
        )

        return {
            "key": "reasoning_quality_score",
            "score": overall_score / 100.0,
            "comment": comment
        }

    @staticmethod
    def compliance_evaluator(score_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangSmith evaluator for Compliance score.

        Args:
            score_data: Dictionary containing compliance score details
                - overall_score: Overall compliance score (0-100)
                - structure_compliance: Structure dimension (0-100)
                - content_compliance: Content dimension (0-100)
                - format_compliance: Format dimension (0-100)
                - length_compliance: Length dimension (0-100)
                - language_compliance: Language dimension (0-100)
                - citation_compliance: Citation dimension (0-100)
                - violations: List of compliance violations

        Returns:
            LangSmith-compatible dict with key, score, comment
        """
        overall_score = score_data.get('overall_score', 0)

        # Build detailed breakdown comment
        structure = score_data.get('structure_compliance', 0)
        content = score_data.get('content_compliance', 0)
        format_comp = score_data.get('format_compliance', 0)
        length = score_data.get('length_compliance', 0)
        language = score_data.get('language_compliance', 0)
        citation = score_data.get('citation_compliance', 0)

        violations = score_data.get('violations', [])
        violation_summary = f" | {len(violations)} violations" if violations else ""

        comment = (
            f"Structure: {structure:.1f}%, Content: {content:.1f}%, "
            f"Format: {format_comp:.1f}%, Length: {length:.1f}%, "
            f"Language: {language:.1f}%, Citation: {citation:.1f}%{violation_summary}"
        )

        return {
            "key": "compliance_score",
            "score": overall_score / 100.0,
            "comment": comment
        }

    @staticmethod
    def qos_evaluator(score_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangSmith evaluator for QoS (Quality of Service) score.

        Args:
            score_data: Dictionary containing QoS score details
                - overall_score: Overall QoS score (0-100)
                - latency_score: Latency dimension (0-100)
                - determinism_score: Determinism dimension (0-100)
                - reliability_score: Reliability dimension (0-100)
                - resource_efficiency_score: Resource efficiency dimension (0-100)
                - scalability_score: Scalability dimension (0-100)
                - total_latency: Total end-to-end latency (seconds)
                - db_queries: Number of database queries
                - llm_calls: Number of LLM calls

        Returns:
            LangSmith-compatible dict with key, score, comment
        """
        overall_score = score_data.get('overall_score', 0)

        # Build detailed breakdown comment
        latency = score_data.get('latency_score', 0)
        determinism = score_data.get('determinism_score', 0)
        reliability = score_data.get('reliability_score', 0)
        resource = score_data.get('resource_efficiency_score', 0)
        scalability = score_data.get('scalability_score', 0)

        total_latency = score_data.get('total_latency', 0)
        db_queries = score_data.get('db_queries', 0)
        llm_calls = score_data.get('llm_calls', 0)

        metrics_summary = (
            f" | Latency: {total_latency:.2f}s, DB: {db_queries}, LLM: {llm_calls}"
        )

        comment = (
            f"Latency: {latency:.1f}%, Determinism: {determinism:.1f}%, "
            f"Reliability: {reliability:.1f}%, Resource: {resource:.1f}%, "
            f"Scalability: {scalability:.1f}%{metrics_summary}"
        )

        return {
            "key": "qos_score",
            "score": overall_score / 100.0,
            "comment": comment
        }

    @staticmethod
    def cost_evaluator(score_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangSmith evaluator for Cost score.

        Args:
            score_data: Dictionary containing cost score details
                - overall_score: Cost efficiency score (0-100)
                - total_cost_thb: Total cost in Thai Baht
                - llm_cost_usd: LLM API cost in USD
                - llm_cost_thb: LLM API cost in Thai Baht
                - db_cost_thb: Database cost in Thai Baht
                - input_tokens: Input tokens used
                - output_tokens: Output tokens used
                - total_tokens: Total tokens used
                - llm_calls: Number of LLM calls

        Returns:
            LangSmith-compatible dict with key, score, comment
        """
        overall_score = score_data.get('overall_score', 0)

        # Build detailed breakdown comment
        total_cost_thb = score_data.get('total_cost_thb', 0)
        llm_cost_usd = score_data.get('llm_cost_usd', 0)

        input_tokens = score_data.get('input_tokens', 0)
        output_tokens = score_data.get('output_tokens', 0)
        total_tokens = score_data.get('total_tokens', 0)
        llm_calls = score_data.get('llm_calls', 0)

        cost_summary = f"฿{total_cost_thb:.2f} (${llm_cost_usd:.4f})"
        token_summary = f"Tokens: {total_tokens:,} ({input_tokens:,}+{output_tokens:,}), Calls: {llm_calls}"

        comment = f"{cost_summary} | {token_summary}"

        return {
            "key": "cost_score",
            "score": overall_score / 100.0,
            "comment": comment
        }

    @classmethod
    def evaluate_all(cls, quality_scores: Dict[str, Any],
                    performance_scores: Dict[str, Any]) -> list[Dict[str, Any]]:
        """
        Evaluate all 6 metrics and return LangSmith-compatible results.

        Args:
            quality_scores: Dict containing all quality scores:
                - faithfulness: Faithfulness score data
                - completeness: Completeness score data
                - reasoning_quality: Reasoning quality score data
                - compliance: Compliance score data
            performance_scores: Dict containing performance scores:
                - qos: QoS score data
                - cost: Cost score data

        Returns:
            List of LangSmith-compatible evaluation results
        """
        results = []

        # Quality metrics
        if 'faithfulness' in quality_scores:
            results.append(cls.faithfulness_evaluator(quality_scores['faithfulness']))

        if 'completeness' in quality_scores:
            results.append(cls.completeness_evaluator(quality_scores['completeness']))

        if 'reasoning_quality' in quality_scores:
            results.append(cls.reasoning_quality_evaluator(quality_scores['reasoning_quality']))

        if 'compliance' in quality_scores:
            results.append(cls.compliance_evaluator(quality_scores['compliance']))

        # Performance metrics
        if 'qos' in performance_scores:
            results.append(cls.qos_evaluator(performance_scores['qos']))

        if 'cost' in performance_scores:
            results.append(cls.cost_evaluator(performance_scores['cost']))

        return results
