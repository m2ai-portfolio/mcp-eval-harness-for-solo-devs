"""Exact string matching with diff generation."""

import difflib
from typing import Optional
from ..models import ComparisonResult, Expectation, ExpectationType

# Maximum input size (1MB)
MAX_INPUT_SIZE = 1_000_000


class ExactComparator:
    """Exact string matching with diff generation."""

    def compare(self, actual: str, expectation: Expectation) -> ComparisonResult:
        """
        Compare actual output against expected value.

        - If exact match: PASS with confidence=1.0
        - If not: Generate unified diff, calculate similarity ratio
        - Use difflib.unified_diff for diff generation
        - Use difflib.SequenceMatcher for similarity ratio

        Args:
            actual: The actual output to compare
            expectation: The expectation to compare against

        Returns:
            ComparisonResult with pass/fail status and details
        """
        expected = expectation.value

        # Check input size limits
        if len(actual) > MAX_INPUT_SIZE or len(expected) > MAX_INPUT_SIZE:
            return ComparisonResult(
                passed=False,
                expectation_type=ExpectationType.EXACT,
                expected=expected,
                actual=actual,
                score=0.0,
                details=f"Input exceeds maximum size of {MAX_INPUT_SIZE} characters"
            )

        # Check for exact match
        if actual == expected:
            return ComparisonResult(
                passed=True,
                expectation_type=ExpectationType.EXACT,
                expected=expected,
                actual=actual,
                score=1.0,
                details="Exact match"
            )

        # Not an exact match - calculate similarity and generate diff
        similarity = difflib.SequenceMatcher(None, expected, actual).ratio()

        # Generate unified diff
        expected_lines = expected.splitlines(keepends=True)
        actual_lines = actual.splitlines(keepends=True)

        diff_lines = list(difflib.unified_diff(
            expected_lines,
            actual_lines,
            fromfile='expected',
            tofile='actual',
            lineterm=''
        ))

        diff_text = ''.join(diff_lines) if diff_lines else "No line-based differences (whitespace/formatting)"

        # Try JSON comparison if both are valid JSON
        json_diff = self._try_json_diff(expected, actual)
        if json_diff:
            diff_text = f"{diff_text}\n\nJSON Structure Differences:\n{json_diff}"

        details = f"Similarity: {similarity:.2%}\n\nDiff:\n{diff_text}"

        return ComparisonResult(
            passed=False,
            expectation_type=ExpectationType.EXACT,
            expected=expected,
            actual=actual,
            score=similarity,
            details=details
        )

    def _try_json_diff(self, expected: str, actual: str) -> Optional[str]:
        """
        Try to parse both as JSON and generate structural diff.

        Args:
            expected: Expected value string
            actual: Actual value string

        Returns:
            JSON diff description or None if not valid JSON
        """
        import json

        try:
            expected_json = json.loads(expected)
            actual_json = json.loads(actual)

            differences = []
            self._compare_json_structures(expected_json, actual_json, "", differences)

            return "\n".join(differences) if differences else None

        except (json.JSONDecodeError, TypeError):
            return None

    def _compare_json_structures(self, expected, actual, path: str, differences: list):
        """
        Recursively compare JSON structures and record differences.

        Args:
            expected: Expected JSON value
            actual: Actual JSON value
            path: Current path in the JSON structure
            differences: List to accumulate difference descriptions
        """
        if type(expected) != type(actual):
            differences.append(f"{path or 'root'}: type mismatch (expected {type(expected).__name__}, got {type(actual).__name__})")
            return

        if isinstance(expected, dict):
            # Check for missing/extra keys
            expected_keys = set(expected.keys())
            actual_keys = set(actual.keys())

            missing = expected_keys - actual_keys
            extra = actual_keys - expected_keys

            if missing:
                differences.append(f"{path or 'root'}: missing keys: {sorted(missing)}")
            if extra:
                differences.append(f"{path or 'root'}: extra keys: {sorted(extra)}")

            # Recursively compare common keys
            for key in expected_keys & actual_keys:
                new_path = f"{path}.{key}" if path else key
                self._compare_json_structures(expected[key], actual[key], new_path, differences)

        elif isinstance(expected, list):
            if len(expected) != len(actual):
                differences.append(f"{path or 'root'}: list length mismatch (expected {len(expected)}, got {len(actual)})")

            # Compare elements up to the shorter length
            for i, (exp_item, act_item) in enumerate(zip(expected, actual)):
                new_path = f"{path}[{i}]" if path else f"[{i}]"
                self._compare_json_structures(exp_item, act_item, new_path, differences)

        elif expected != actual:
            differences.append(f"{path or 'root'}: value mismatch (expected {expected!r}, got {actual!r})")
