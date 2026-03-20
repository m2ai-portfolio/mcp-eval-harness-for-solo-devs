"""Reporting and metrics export for MCP Eval Harness."""

import logging
from .console import ConsoleReporter
from .json import JSONExporter
from .csv_export import CSVExporter
from .regression import RegressionDetector, BaselineManager, RegressionIssue, RegressionCategory

logger = logging.getLogger(__name__)

# Default cost models (per 1000 tokens)
DEFAULT_COST_MODELS = {
    "gpt-4": {"prompt": 0.03, "completion": 0.06},
    "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
    "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
    "claude-3-opus": {"prompt": 0.015, "completion": 0.075},
    "claude-3-sonnet": {"prompt": 0.003, "completion": 0.015},
    "claude-3-haiku": {"prompt": 0.00025, "completion": 0.00125},
}


def calculate_cost(prompt_tokens: int, completion_tokens: int, model: str, cost_models: dict = None) -> float:
    """
    Calculate estimated cost from token usage.

    Args:
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        model: Model name (e.g., "gpt-4", "claude-3-opus")
        cost_models: Optional custom cost models to use

    Returns:
        Estimated cost in USD
    """
    models = cost_models or DEFAULT_COST_MODELS

    if model not in models:
        logger.warning(f"Unknown model '{model}', defaulting to GPT-4 pricing")
        model = "gpt-4"

    pricing = models[model]
    prompt_cost = (prompt_tokens * pricing["prompt"]) / 1000
    completion_cost = (completion_tokens * pricing["completion"]) / 1000

    return round(prompt_cost + completion_cost, 6)


__all__ = [
    'ConsoleReporter',
    'JSONExporter',
    'CSVExporter',
    'RegressionDetector',
    'BaselineManager',
    'RegressionIssue',
    'RegressionCategory',
    'DEFAULT_COST_MODELS',
    'calculate_cost',
]
