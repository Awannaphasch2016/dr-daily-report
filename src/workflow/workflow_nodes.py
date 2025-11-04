"""Workflow nodes for LangGraph ticker analysis agent"""

from typing import TypedDict
import time
import json
from datetime import datetime
import pandas as pd
from langchain_core.messages import HumanMessage

from src.types import AgentState


class WorkflowNodes:
    """Encapsulates all LangGraph workflow node methods"""
    
    def __init__(
        self,
        data_fetcher,
        technical_analyzer,
        news_fetcher,
        chart_generator,
        db,
        strategy_backtester,
        strategy_analyzer,
        comparative_analyzer,
        llm,
        context_builder,
        prompt_builder,
        market_analyzer,
        number_injector,
        cost_scorer,
        scoring_service,
        qos_scorer,
        faithfulness_scorer,
        completeness_scorer,
        reasoning_quality_scorer,
        compliance_scorer,
        ticker_map,
        db_query_count_ref
    ):
        """
        Initialize WorkflowNodes with all required dependencies
        
        Args:
            db_query_count_ref: Reference to _db_query_count from agent (for shared state)
        """
        self.data_fetcher = data_fetcher
        self.technical_analyzer = technical_analyzer
        self.news_fetcher = news_fetcher
        self.chart_generator = chart_generator
        self.db = db
        self.strategy_backtester = strategy_backtester
        self.strategy_analyzer = strategy_analyzer
        self.comparative_analyzer = comparative_analyzer
        self.llm = llm
        self.context_builder = context_builder
        self.prompt_builder = prompt_builder
        self.market_analyzer = market_analyzer
        self.number_injector = number_injector
        self.cost_scorer = cost_scorer
        self.scoring_service = scoring_service
        self.qos_scorer = qos_scorer
        self.faithfulness_scorer = faithfulness_scorer
        self.completeness_scorer = completeness_scorer
        self.reasoning_quality_scorer = reasoning_quality_scorer
        self.compliance_scorer = compliance_scorer
        self.ticker_map = ticker_map
        self._db_query_count_ref = db_query_count_ref
    
    def fetch_data(self, state: AgentState) -> AgentState:
        """Fetch ticker data from Yahoo Finance"""
        start_time = time.perf_counter()
        ticker = state["ticker"]

        # Reset query count at start of new run
        self._db_query_count_ref[0] = 0

        # Get Yahoo ticker from symbol
        yahoo_ticker = self.ticker_map.get(ticker.upper())

        if not yahoo_ticker:
            state["error"] = f"ไม่พบข้อมูล ticker สำหรับ {ticker}"
            return state

        # Fetch data
        data = self.data_fetcher.fetch_ticker_data(yahoo_ticker)

        if not data:
            state["error"] = f"ไม่สามารถดึงข้อมูลสำหรับ {ticker} ({yahoo_ticker}) ได้"
            return state

        # Get additional info
        info = self.data_fetcher.get_ticker_info(yahoo_ticker)
        data.update(info)

        # Save to database
        self.db.insert_ticker_data(
            ticker, yahoo_ticker, data['date'],
            {
                'open': data['open'],
                'high': data['high'],
                'low': data['low'],
                'close': data['close'],
                'volume': data['volume'],
                'market_cap': data.get('market_cap'),
                'pe_ratio': data.get('pe_ratio'),
                'eps': data.get('eps'),
                'dividend_yield': data.get('dividend_yield')
            }
        )
        self._db_query_count_ref[0] += 1

        # Record timing
        elapsed = time.perf_counter() - start_time
        timing_metrics = state.get("timing_metrics", {})
        timing_metrics["data_fetch"] = elapsed
        state["timing_metrics"] = timing_metrics

        state["ticker_data"] = data
        return state

    def fetch_news(self, state: AgentState) -> AgentState:
        """Fetch high-impact news for the ticker"""
        if state.get("error"):
            return state

        start_time = time.perf_counter()
        yahoo_ticker = self.ticker_map.get(state["ticker"].upper())
        if not yahoo_ticker:
            state["news"] = []
            state["news_summary"] = {}
            return state

        # Fetch high-impact news (min score 40, max 5 items)
        high_impact_news = self.news_fetcher.filter_high_impact_news(
            yahoo_ticker,
            min_score=40.0,
            max_news=5
        )

        # Get news summary statistics
        news_summary = self.news_fetcher.get_news_summary(high_impact_news)

        # Record timing
        elapsed = time.perf_counter() - start_time
        timing_metrics = state.get("timing_metrics", {})
        timing_metrics["news_fetch"] = elapsed
        state["timing_metrics"] = timing_metrics

        state["news"] = high_impact_news
        state["news_summary"] = news_summary

        return state

    def analyze_technical(self, state: AgentState) -> AgentState:
        """Analyze technical indicators with percentile analysis"""
        if state.get("error"):
            return state

        start_time = time.perf_counter()
        ticker_data = state["ticker_data"]
        hist_data = ticker_data.get('history')

        if hist_data is None or hist_data.empty:
            state["error"] = "ไม่มีข้อมูลประวัติสำหรับการวิเคราะห์"
            return state

        # Calculate indicators with percentiles
        result = self.technical_analyzer.calculate_all_indicators_with_percentiles(hist_data)

        if not result or not result.get('indicators'):
            state["error"] = "ไม่สามารถคำนวณ indicators ได้"
            return state

        indicators = result['indicators']
        percentiles = result.get('percentiles', {})
        chart_patterns = result.get('chart_patterns', [])
        pattern_statistics = result.get('pattern_statistics', {})

        # Calculate strategy performance
        strategy_performance = {}
        if self.strategy_backtester:
            try:
                buy_results = self.strategy_backtester.backtest_buy_only(hist_data)
                sell_results = self.strategy_backtester.backtest_sell_only(hist_data)
                
                if buy_results and sell_results:
                    strategy_performance = {
                        'buy_only': buy_results,
                        'sell_only': sell_results,
                        'last_buy_signal': self.strategy_analyzer.get_last_buy_signal(hist_data),
                        'last_sell_signal': self.strategy_analyzer.get_last_sell_signal(hist_data)
                    }
            except Exception as e:
                print(f"Error calculating strategy performance: {str(e)}")
                strategy_performance = {}

        # Save indicators to database
        yahoo_ticker = self.ticker_map.get(state["ticker"].upper())
        if yahoo_ticker:  # Only save if ticker is in the map
            self.db.insert_technical_indicators(
                yahoo_ticker, ticker_data['date'], indicators
            )
            self._db_query_count_ref[0] += 1

        # Record timing
        elapsed = time.perf_counter() - start_time
        timing_metrics = state.get("timing_metrics", {})
        timing_metrics["technical_analysis"] = elapsed
        state["timing_metrics"] = timing_metrics

        state["indicators"] = indicators
        state["percentiles"] = percentiles
        state["chart_patterns"] = chart_patterns
        state["pattern_statistics"] = pattern_statistics
        state["strategy_performance"] = strategy_performance
        return state

    def generate_chart(self, state: AgentState) -> AgentState:
        """Generate technical analysis chart"""
        if state.get("error"):
            return state

        start_time = time.perf_counter()
        try:
            ticker = state["ticker"]
            ticker_data = state["ticker_data"]
            indicators = state["indicators"]

            # Generate chart (90 days by default)
            chart_base64 = self.chart_generator.generate_chart(
                ticker_data=ticker_data,
                indicators=indicators,
                ticker_symbol=ticker,
                days=90
            )

            state["chart_base64"] = chart_base64
            print(f"✅ Chart generated for {ticker}")

        except Exception as e:
            print(f"⚠️  Chart generation failed: {str(e)}")
            # Don't set error - chart is optional, continue without it
            state["chart_base64"] = ""

        # Record timing (even if failed)
        elapsed = time.perf_counter() - start_time
        timing_metrics = state.get("timing_metrics", {})
        timing_metrics["chart_generation"] = elapsed
        state["timing_metrics"] = timing_metrics

        return state

    def generate_report(self, state: AgentState) -> AgentState:
        """Generate Thai language report using LLM"""
        if state.get("error"):
            return state

        llm_start_time = time.perf_counter()
        ticker = state["ticker"]
        ticker_data = state["ticker_data"]
        indicators = state["indicators"]
        percentiles = state.get("percentiles", {})
        chart_patterns = state.get("chart_patterns", [])
        pattern_statistics = state.get("pattern_statistics", {})
        strategy_performance = state.get("strategy_performance", {})
        news = state.get("news", [])
        news_summary = state.get("news_summary", {})

        # Initialize API costs tracking
        api_costs = state.get("api_costs", {})
        total_input_tokens = 0
        total_output_tokens = 0
        llm_calls = 0

        # First pass: Generate report without strategy data to determine recommendation
        comparative_insights = state.get("comparative_insights", {})
        context = self.context_builder.prepare_context(ticker, ticker_data, indicators, percentiles, news, news_summary, strategy_performance=None, comparative_insights=comparative_insights)
        uncertainty_score = indicators.get('uncertainty_score', 0)
        
        prompt = self.prompt_builder.build_prompt(context, uncertainty_score, strategy_performance=None)
        response = self.llm.invoke([HumanMessage(content=prompt)])
        initial_report = response.content
        llm_calls += 1

        # Extract token usage from response
        response_metadata = getattr(response, 'response_metadata', {})
        usage = response_metadata.get('token_usage', {})
        if usage:
            total_input_tokens += usage.get('prompt_tokens', 0)
            total_output_tokens += usage.get('completion_tokens', 0)
        else:
            # Fallback: estimate tokens (rough approximation: 4 chars per token)
            total_input_tokens += len(prompt) // 4
            total_output_tokens += len(initial_report) // 4

        # Extract recommendation from initial report
        recommendation = self.strategy_analyzer.extract_recommendation(initial_report)
        
        # Check if strategy performance aligns with recommendation
        include_strategy = self.strategy_analyzer.check_strategy_alignment(recommendation, strategy_performance)
        
        # Second pass: If aligned, regenerate with strategy data
        if include_strategy and strategy_performance:
            context_with_strategy = self.context_builder.prepare_context(
                ticker, ticker_data, indicators, percentiles, news, news_summary, strategy_performance=strategy_performance, comparative_insights=comparative_insights
            )
            prompt_with_strategy = self.prompt_builder.build_prompt(context_with_strategy, uncertainty_score, strategy_performance=strategy_performance)
            response = self.llm.invoke([HumanMessage(content=prompt_with_strategy)])
            report = response.content
            llm_calls += 1

            # Extract token usage from second response
            response_metadata = getattr(response, 'response_metadata', {})
            usage = response_metadata.get('token_usage', {})
            if usage:
                total_input_tokens += usage.get('prompt_tokens', 0)
                total_output_tokens += usage.get('completion_tokens', 0)
            else:
                total_input_tokens += len(prompt_with_strategy) // 4
                total_output_tokens += len(report) // 4
        else:
            report = initial_report

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # INJECT DETERMINISTIC NUMBERS (Damodaran "narrative + number" approach)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Calculate ground truth for injection
        conditions = self.market_analyzer.calculate_market_conditions(indicators)
        ground_truth = {
            'uncertainty_score': indicators.get('uncertainty_score', 0),
            'atr_pct': (indicators.get('atr', 0) / indicators.get('current_price', 1)) * 100 if indicators.get('current_price', 0) > 0 else 0,
            'vwap_pct': conditions.get('price_vs_vwap_pct', 0),
            'volume_ratio': conditions.get('volume_ratio', 0),
        }

        # Replace all {{PLACEHOLDERS}} with exact ground truth values
        report = self.number_injector.inject_deterministic_numbers(
            report, ground_truth, indicators, percentiles
        )
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        # Record LLM timing
        llm_elapsed = time.perf_counter() - llm_start_time
        timing_metrics = state.get("timing_metrics", {})
        timing_metrics["llm_generation"] = llm_elapsed
        state["timing_metrics"] = timing_metrics

        # Calculate API costs
        api_costs = self.cost_scorer.calculate_api_cost(
            total_input_tokens, total_output_tokens, actual_cost_usd=None
        )
        state["api_costs"] = api_costs

        # Add news references at the end if news exists
        if news:
            news_references = self.news_fetcher.get_news_references(news)
            report += f"\n\n{news_references}"
        
        # Add percentile analysis at the end
        if percentiles:
            percentile_analysis = self.technical_analyzer.format_percentile_analysis(percentiles)
            report += f"\n\n{percentile_analysis}"

        # Build scoring context for storage and scoring
        # Convert datetime/DataFrame objects to JSON-serializable format
        def make_json_serializable(obj):
            """Recursively convert datetime/date/DataFrame objects to JSON-serializable format"""
            from datetime import date
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            elif isinstance(obj, pd.Timestamp):
                return obj.isoformat()
            elif isinstance(obj, pd.DataFrame):
                # Convert DataFrame to list of records (handles timestamp indexes)
                df_copy = obj.reset_index(drop=False)
                return make_json_serializable(df_copy.to_dict('records'))
            elif isinstance(obj, dict):
                # Convert dict keys and values
                return {str(k) if isinstance(k, (pd.Timestamp, datetime, date)) else k: make_json_serializable(v)
                        for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_json_serializable(item) for item in obj]
            return obj

        market_conditions = self.market_analyzer.calculate_market_conditions(indicators)
        from src.scoring_service import ScoringContext
        scoring_context = ScoringContext(
            indicators=make_json_serializable(indicators),
            percentiles=make_json_serializable(percentiles),
            news=make_json_serializable(news),
            ticker_data=make_json_serializable(ticker_data),
            market_conditions={
                'uncertainty_score': indicators.get('uncertainty_score', 0),
                'atr_pct': (indicators.get('atr', 0) / indicators.get('current_price', 1)) * 100 if indicators.get('current_price', 0) > 0 else 0,
                'price_vs_vwap_pct': market_conditions.get('price_vs_vwap_pct', 0),
                'volume_ratio': market_conditions.get('volume_ratio', 0),
            },
            comparative_insights=make_json_serializable(state.get('comparative_insights', {}))
        )

        # Save report with context to database
        yahoo_ticker = self.ticker_map.get(ticker.upper())
        self.db.save_report(
            yahoo_ticker,
            ticker_data['date'],
            {
                'report_text': report,
                'context_json': json.dumps(scoring_context.to_json()),
                'technical_summary': self.technical_analyzer.analyze_trend(indicators, indicators.get('current_price')),
                'fundamental_summary': f"P/E: {ticker_data.get('pe_ratio', 'N/A')}",
                'sector_analysis': ticker_data.get('sector', 'N/A')
            }
        )
        self._db_query_count_ref[0] += 1

        state["report"] = report

        # Score narrative using ScoringService (with timing)
        scoring_start_time = time.perf_counter()

        # Compute all quality scores using service layer
        quality_scores = self.scoring_service.compute_all_quality_scores(report, scoring_context)

        faithfulness_score = quality_scores['faithfulness']
        completeness_score = quality_scores['completeness']
        reasoning_quality_score = quality_scores['reasoning_quality']
        compliance_score = quality_scores['compliance']

        state["faithfulness_score"] = faithfulness_score
        state["completeness_score"] = completeness_score
        state["reasoning_quality_score"] = reasoning_quality_score
        state["compliance_score"] = compliance_score

        # Record scoring timing
        scoring_elapsed = time.perf_counter() - scoring_start_time
        timing_metrics["scoring"] = scoring_elapsed
        state["timing_metrics"] = timing_metrics

        # Calculate total latency
        total_latency = sum(timing_metrics.values())
        timing_metrics["total"] = total_latency
        state["timing_metrics"] = timing_metrics

        # Prepare database metrics
        database_metrics = {
            'query_count': self._db_query_count_ref[0],
            'cache_hit': False  # Could be enhanced with cache checking
        }
        state["database_metrics"] = database_metrics

        # Calculate QoS score
        historical_data = self.db.get_historical_qos(yahoo_ticker) if yahoo_ticker else None
        
        qos_score = self.qos_scorer.score_qos(
            timing_metrics=timing_metrics,
            database_metrics=database_metrics,
            error_occurred=bool(state.get("error")),
            cache_hit=False,
            llm_calls=llm_calls,
            historical_data=historical_data
        )
        state["qos_score"] = qos_score

        # Calculate Cost score
        cost_score = self.cost_scorer.score_cost(
            api_costs=api_costs,
            llm_calls=llm_calls,
            database_metrics=database_metrics,
            cache_hit=False
        )
        state["cost_score"] = cost_score

        # Save all scores to database
        if yahoo_ticker:
            # Save quality scores
            self.db.save_faithfulness_score(yahoo_ticker, ticker_data['date'], faithfulness_score)
            self.db.save_completeness_score(yahoo_ticker, ticker_data['date'], completeness_score)
            self.db.save_reasoning_quality_score(yahoo_ticker, ticker_data['date'], reasoning_quality_score)
            self.db.save_compliance_score(yahoo_ticker, ticker_data['date'], compliance_score)

            # Save performance metrics
            self.db.save_qos_metrics(yahoo_ticker, ticker_data['date'], qos_score)
            self.db.save_cost_metrics(yahoo_ticker, ticker_data['date'], cost_score)

            # Save aggregated summary
            self.db.save_score_summary(yahoo_ticker, ticker_data['date'], {
                'faithfulness': faithfulness_score,
                'completeness': completeness_score,
                'reasoning_quality': reasoning_quality_score,
                'compliance': compliance_score,
                'qos': qos_score,
                'cost': cost_score
            })

        # Print all score reports
        print("\n" + self.faithfulness_scorer.format_score_report(faithfulness_score))
        print("\n" + self.completeness_scorer.format_score_report(completeness_score))
        print("\n" + self.reasoning_quality_scorer.format_score_report(reasoning_quality_score))
        print("\n" + self.compliance_scorer.format_score_report(compliance_score))
        print("\n" + self.qos_scorer.format_score_report(qos_score))
        print("\n" + self.cost_scorer.format_score_report(cost_score))

        # Reset query count for next run
        self._db_query_count_ref[0] = 0

        return state

    def fetch_comparative_data(self, state: AgentState) -> AgentState:
        """Fetch historical data for comparative analysis with similar tickers"""
        if state.get("error"):
            return state
        
        start_time = time.perf_counter()
        ticker = state["ticker"]
        yahoo_ticker = self.ticker_map.get(ticker.upper())
        
        if not yahoo_ticker:
            state["comparative_data"] = {}
            return state
        
        try:
            # Get similar tickers from the same sector or nearby tickers in our list
            # For now, fetch 3-5 other tickers from our ticker list for comparison
            all_tickers = list(self.ticker_map.keys())
            similar_tickers = []
            
            # Find tickers in same sector if available
            ticker_data = state.get("ticker_data", {})
            sector = ticker_data.get("sector")
            
            # Get 3-5 other tickers (excluding current ticker)
            for t in all_tickers:
                if t != ticker.upper() and len(similar_tickers) < 5:
                    similar_tickers.append(t)
            
            # Fetch historical data for comparative analysis
            comparative_data = {}
            for t in similar_tickers[:5]:  # Limit to 5 to avoid too many API calls
                yt = self.ticker_map.get(t)
                if yt:
                    try:
                        hist_data = self.data_fetcher.fetch_historical_data(yt, days=90)
                        if hist_data is not None and not hist_data.empty:
                            comparative_data[t] = hist_data
                    except Exception as e:
                        print(f"⚠️  Failed to fetch comparative data for {t}: {str(e)}")
                        continue
            
            state["comparative_data"] = comparative_data
            print(f"✅ Fetched comparative data for {len(comparative_data)} tickers")
            
        except Exception as e:
            print(f"⚠️  Comparative data fetch failed: {str(e)}")
            state["comparative_data"] = {}
        
        # Record timing
        elapsed = time.perf_counter() - start_time
        timing_metrics = state.get("timing_metrics", {})
        timing_metrics["comparative_data_fetch"] = elapsed
        state["timing_metrics"] = timing_metrics
        
        return state
    
    def analyze_comparative_insights(self, state: AgentState) -> AgentState:
        """Perform comparative analysis and extract narrative-ready insights"""
        if state.get("error"):
            return state
        
        start_time = time.perf_counter()
        ticker = state["ticker"]
        ticker_data = state.get("ticker_data", {})
        indicators = state.get("indicators", {})
        comparative_data = state.get("comparative_data", {})
        
        if not comparative_data:
            state["comparative_insights"] = {}
            return state
        
        try:
            # Add current ticker's data to comparative dataset
            yahoo_ticker = self.ticker_map.get(ticker.upper())
            if yahoo_ticker and ticker_data.get("history") is not None:
                hist_data = ticker_data.get("history")
                if hist_data is not None and not hist_data.empty:
                    comparative_data[ticker.upper()] = hist_data
            
            # Perform comprehensive comparative analysis
            if len(comparative_data) >= 2:
                analysis_results = self.comparative_analyzer.comprehensive_analysis(comparative_data)
                
                # Extract narrative-ready insights
                insights = self._extract_narrative_insights(ticker, indicators, analysis_results, comparative_data)
                state["comparative_insights"] = insights
                print(f"✅ Generated comparative insights for {ticker}")
            else:
                state["comparative_insights"] = {}
                
        except Exception as e:
            print(f"⚠️  Comparative analysis failed: {str(e)}")
            state["comparative_insights"] = {}
        
        # Record timing
        elapsed = time.perf_counter() - start_time
        timing_metrics = state.get("timing_metrics", {})
        timing_metrics["comparative_analysis"] = elapsed
        state["timing_metrics"] = timing_metrics
        
        return state
    
    def _extract_narrative_insights(self, target_ticker: str, indicators: dict, analysis_results: dict, comparative_data: dict) -> dict:
        """Extract insights that can be woven into narrative in Damodaran style"""
        insights = {}
        
        if 'error' in analysis_results:
            return insights
        
        # Get correlation insights
        if 'correlation_matrix' in analysis_results:
            corr_dict = analysis_results['correlation_matrix']
            if isinstance(corr_dict, dict):
                corr_matrix = pd.DataFrame(corr_dict)
            else:
                corr_matrix = corr_dict
            
            if not corr_matrix.empty and target_ticker.upper() in corr_matrix.index:
                # Find most similar tickers
                similar = self.comparative_analyzer.find_similar_tickers(
                    corr_matrix, target_ticker.upper(), top_n=3
                )
                insights['similar_tickers'] = similar
                
                # Average correlation
                target_corrs = corr_matrix.loc[target_ticker.upper()].drop(target_ticker.upper())
                insights['avg_correlation'] = float(target_corrs.mean()) if len(target_corrs) > 0 else None
        
        # Get clustering insights
        if 'clustering' in analysis_results:
            clustering = analysis_results['clustering']
            clusters = self.comparative_analyzer.get_ticker_clusters(clustering)
            
            # Find which cluster target ticker is in
            for cluster_id, tickers in clusters.items():
                if target_ticker.upper() in tickers:
                    insights['cluster_id'] = cluster_id
                    insights['cluster_members'] = [t for t in tickers if t != target_ticker.upper()][:3]
                    break
        
        # Get feature comparison insights
        if 'features' in analysis_results:
            features_df = analysis_results['features']
            if not features_df.empty and 'ticker' in features_df.columns:
                # Set ticker as index for easier access
                features_df_indexed = features_df.set_index('ticker')
                
                if target_ticker.upper() in features_df_indexed.index:
                    target_features = features_df_indexed.loc[target_ticker.upper()]
                    
                    # Compare volatility, returns, sharpe ratio
                    insights['volatility_vs_peers'] = {
                        'current': float(target_features.get('volatility', 0)),
                        'peer_avg': float(features_df_indexed['volatility'].mean()) if 'volatility' in features_df_indexed.columns else None
                    }
                    
                    insights['return_vs_peers'] = {
                        'current': float(target_features.get('mean_return', 0)),
                        'peer_avg': float(features_df_indexed['mean_return'].mean()) if 'mean_return' in features_df_indexed.columns else None
                    }
                    
                    insights['sharpe_vs_peers'] = {
                        'current': float(target_features.get('sharpe_ratio', 0)),
                        'peer_avg': float(features_df_indexed['sharpe_ratio'].mean()) if 'sharpe_ratio' in features_df_indexed.columns else None
                    }
                    
                    # Rank position
                    if 'volatility' in features_df_indexed.columns:
                        vol_rank = (features_df_indexed['volatility'] < target_features['volatility']).sum() + 1
                        insights['volatility_rank'] = {
                            'position': int(vol_rank),
                            'total': len(features_df_indexed)
                        }
        
        return insights
