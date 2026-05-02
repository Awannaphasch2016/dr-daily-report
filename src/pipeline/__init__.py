"""Report generation pipeline — split into PreProcess, Generation, PostProcess phases.

Orchestrated by Step Functions Express workflow. Each phase runs as a separate Lambda
sharing the same Docker image with different handler entry points.

Modules:
    s3_payload: S3 read/write for intermediate AgentState between phases
    data_pipeline: Data-only LangGraph (no generate_report node)
    single_pass_strategy: Extracted single-pass LLM generation logic
    postprocess: Number injection + scoring + trace storage
"""
