"""Semantic similarity comparison using stdlib only."""

import difflib
import re
from ..models import ComparisonResult, Expectation, ExpectationType

# Maximum input size (1MB)
MAX_INPUT_SIZE = 1_000_000


class SemanticComparator:
    """Semantic similarity comparison."""

    def compare(self, actual: str, expectation: Expectation) -> ComparisonResult:
        """
        Calculate semantic similarity between actual and expected.

        - Use difflib.SequenceMatcher as the baseline similarity metric
        - Also implement a token-overlap (bag-of-words) similarity score
        - Combine both scores for a composite similarity
        - Use expectation.threshold (default 0.8) as pass threshold

        Args:
            actual: The actual output to compare
            expectation: The expectation with expected value and threshold

        Returns:
            ComparisonResult with similarity score and pass/fail status
        """
        expected = expectation.value
        threshold = expectation.threshold if expectation.threshold is not None else 0.8

        # Check input size limits
        if len(actual) > MAX_INPUT_SIZE or len(expected) > MAX_INPUT_SIZE:
            return ComparisonResult(
                passed=False,
                expectation_type=ExpectationType.SEMANTIC,
                expected=expected,
                actual=actual,
                score=0.0,
                details=f"Input exceeds maximum size of {MAX_INPUT_SIZE} characters"
            )

        # Calculate sequence similarity using SequenceMatcher
        sequence_ratio = difflib.SequenceMatcher(None, expected, actual).ratio()

        # Calculate token overlap (Jaccard similarity)
        token_overlap = self._calculate_token_overlap(expected, actual)

        # Combine both scores: 60% sequence similarity + 40% token overlap
        combined_score = (0.6 * sequence_ratio) + (0.4 * token_overlap)

        # Check if it passes the threshold
        passed = combined_score >= threshold

        # Build details
        details_lines = [
            f"Sequence similarity: {sequence_ratio:.2%}",
            f"Token overlap (Jaccard): {token_overlap:.2%}",
            f"Combined score: {combined_score:.2%}",
            f"Threshold: {threshold:.2%}",
            f"Result: {'PASS' if passed else 'FAIL'}"
        ]

        # Add a few similar/different tokens for context
        expected_tokens = set(self._tokenize(expected))
        actual_tokens = set(self._tokenize(actual))
        common = expected_tokens & actual_tokens
        missing = expected_tokens - actual_tokens
        extra = actual_tokens - expected_tokens

        if common:
            details_lines.append(f"\nCommon tokens ({len(common)}): {', '.join(sorted(list(common)[:10]))}")
            if len(common) > 10:
                details_lines[-1] += "..."

        if missing:
            details_lines.append(f"Missing tokens ({len(missing)}): {', '.join(sorted(list(missing)[:5]))}")
            if len(missing) > 5:
                details_lines[-1] += "..."

        if extra:
            details_lines.append(f"Extra tokens ({len(extra)}): {', '.join(sorted(list(extra)[:5]))}")
            if len(extra) > 5:
                details_lines[-1] += "..."

        details = "\n".join(details_lines)

        return ComparisonResult(
            passed=passed,
            expectation_type=ExpectationType.SEMANTIC,
            expected=expected,
            actual=actual,
            score=combined_score,
            details=details
        )

    def _tokenize(self, text: str) -> list:
        """
        Tokenize text into words (alphanumeric tokens).

        Args:
            text: Text to tokenize

        Returns:
            List of lowercase tokens
        """
        # Split on whitespace and punctuation, keep only alphanumeric
        tokens = re.findall(r'\w+', text.lower())
        return tokens

    def _calculate_token_overlap(self, expected: str, actual: str) -> float:
        """
        Calculate Jaccard similarity based on token overlap.

        Jaccard = |intersection| / |union|

        Args:
            expected: Expected text
            actual: Actual text

        Returns:
            Jaccard similarity score (0.0 to 1.0)
        """
        expected_tokens = set(self._tokenize(expected))
        actual_tokens = set(self._tokenize(actual))

        if not expected_tokens and not actual_tokens:
            return 1.0  # Both empty = perfect match

        if not expected_tokens or not actual_tokens:
            return 0.0  # One empty, one not = no match

        intersection = expected_tokens & actual_tokens
        union = expected_tokens | actual_tokens

        return len(intersection) / len(union) if union else 0.0
