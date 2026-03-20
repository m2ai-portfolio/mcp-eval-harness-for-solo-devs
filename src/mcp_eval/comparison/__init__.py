"""Intelligent result comparison module for MCP Eval Harness."""

from .exact import ExactComparator
from .regex import RegexComparator
from .semantic import SemanticComparator
from .custom import CustomComparator

from ..models import ComparisonResult, Expectation, ExpectationType


def compare_result(actual: str, expectation: Expectation) -> ComparisonResult:
    """
    Compare an actual result against an expectation using the appropriate strategy.

    Args:
        actual: The actual output from the agent
        expectation: The expectation to compare against

    Returns:
        ComparisonResult with pass/fail status and details
    """
    comparators = {
        ExpectationType.EXACT: ExactComparator(),
        ExpectationType.REGEX: RegexComparator(),
        ExpectationType.SEMANTIC: SemanticComparator(),
        ExpectationType.CUSTOM: CustomComparator(),
    }

    comparator = comparators[expectation.type]
    return comparator.compare(actual, expectation)


__all__ = [
    'compare_result',
    'ExactComparator',
    'RegexComparator',
    'SemanticComparator',
    'CustomComparator',
    'ComparisonResult',
    'Expectation',
    'ExpectationType',
]
