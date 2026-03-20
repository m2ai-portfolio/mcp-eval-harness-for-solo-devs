"""Regex pattern matching with named capture groups."""

import re
from ..models import ComparisonResult, Expectation, ExpectationType

# Maximum input size for regex matching (100KB to prevent ReDoS)
MAX_INPUT_SIZE = 100_000


class RegexComparator:
    """Regex pattern matching with named capture groups."""

    def compare(self, actual: str, expectation: Expectation) -> ComparisonResult:
        """
        Match actual output against regex pattern.

        - Full match or search match
        - Extract named capture groups
        - Support multiline patterns
        - Return captured groups in the result

        Args:
            actual: The actual output to match
            expectation: The expectation containing the regex pattern

        Returns:
            ComparisonResult with match status and captured groups
        """
        pattern = expectation.value

        # Check input size limits (protection against ReDoS)
        if len(actual) > MAX_INPUT_SIZE or len(pattern) > MAX_INPUT_SIZE:
            return ComparisonResult(
                passed=False,
                expectation_type=ExpectationType.REGEX,
                expected=pattern,
                actual=actual,
                score=0.0,
                details=f"Input exceeds maximum size of {MAX_INPUT_SIZE} characters"
            )

        try:
            # Compile the regex pattern with multiline support
            compiled_pattern = re.compile(pattern, re.MULTILINE | re.DOTALL)

            # Try full match first, then search
            match = compiled_pattern.fullmatch(actual)
            match_type = "fullmatch"

            if not match:
                match = compiled_pattern.search(actual)
                match_type = "search"

            if match:
                # Extract all groups (both named and numbered)
                groups_info = []

                # Named groups
                if match.groupdict():
                    groups_info.append("Named groups:")
                    for name, value in match.groupdict().items():
                        groups_info.append(f"  {name}: {value!r}")

                # Numbered groups (excluding group 0 which is the whole match)
                if match.groups():
                    if groups_info:  # Add separator if we have named groups
                        groups_info.append("")
                    groups_info.append("Captured groups:")
                    for i, group in enumerate(match.groups(), 1):
                        groups_info.append(f"  Group {i}: {group!r}")

                if match_type == "search":
                    groups_info.insert(0, f"Match found at position {match.start()}-{match.end()}")
                    groups_info.insert(1, f"Matched text: {match.group(0)!r}")
                    groups_info.insert(2, "")

                details = "\n".join(groups_info) if groups_info else f"Pattern matched ({match_type})"

                return ComparisonResult(
                    passed=True,
                    expectation_type=ExpectationType.REGEX,
                    expected=pattern,
                    actual=actual,
                    score=1.0,
                    details=details
                )
            else:
                return ComparisonResult(
                    passed=False,
                    expectation_type=ExpectationType.REGEX,
                    expected=pattern,
                    actual=actual,
                    score=0.0,
                    details="Pattern did not match"
                )

        except re.error as e:
            # Invalid regex pattern
            return ComparisonResult(
                passed=False,
                expectation_type=ExpectationType.REGEX,
                expected=pattern,
                actual=actual,
                score=0.0,
                details=f"Invalid regex pattern: {str(e)}"
            )
