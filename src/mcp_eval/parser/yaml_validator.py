"""YAML frontmatter validation for test cases."""

import yaml
from typing import Dict, Any, List
from pydantic import ValidationError
from ..models import TestMetadata


class YAMLValidationError(Exception):
    """Custom exception for YAML validation errors."""
    pass


def validate_yaml_frontmatter(yaml_content: str) -> TestMetadata:
    """
    Validate YAML frontmatter against TestMetadata schema.

    Args:
        yaml_content: Raw YAML content string

    Returns:
        TestMetadata instance

    Raises:
        YAMLValidationError: If YAML is invalid or doesn't match schema
    """
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise YAMLValidationError(f"Invalid YAML syntax: {str(e)}")

    if not isinstance(data, dict):
        raise YAMLValidationError("YAML frontmatter must be a dictionary")

    # Check for required fields
    if "name" not in data:
        raise YAMLValidationError("Missing required field: 'name'")

    # Validate types of common fields with helpful messages
    if "timeout" in data and not isinstance(data["timeout"], int):
        raise YAMLValidationError(
            f"Field 'timeout' must be an integer, got {type(data['timeout']).__name__}"
        )

    if "retries" in data and not isinstance(data["retries"], int):
        raise YAMLValidationError(
            f"Field 'retries' must be an integer, got {type(data['retries']).__name__}"
        )

    if "critical" in data and not isinstance(data["critical"], bool):
        raise YAMLValidationError(
            f"Field 'critical' must be a boolean, got {type(data['critical']).__name__}"
        )

    if "tags" in data and not isinstance(data["tags"], list):
        raise YAMLValidationError(
            f"Field 'tags' must be a list, got {type(data['tags']).__name__}"
        )

    if "cost_threshold" in data and not isinstance(data["cost_threshold"], (int, float, type(None))):
        raise YAMLValidationError(
            f"Field 'cost_threshold' must be a number, got {type(data['cost_threshold']).__name__}"
        )

    # Validate with Pydantic
    try:
        metadata = TestMetadata(**data)
    except ValidationError as e:
        # Convert Pydantic error to friendly message
        error_messages = []
        for error in e.errors():
            field = ".".join(str(x) for x in error["loc"])
            msg = error["msg"]
            error_messages.append(f"Field '{field}': {msg}")
        raise YAMLValidationError("Validation errors:\n  " + "\n  ".join(error_messages))

    # Check for unknown fields (warn but don't fail)
    known_fields = set(TestMetadata.model_fields.keys())
    unknown_fields = set(data.keys()) - known_fields
    if unknown_fields:
        import warnings
        warnings.warn(
            f"Unknown fields in test metadata (will be ignored): {', '.join(unknown_fields)}"
        )

    return metadata


def parse_yaml_frontmatter(content: str) -> tuple[TestMetadata, str]:
    """
    Extract and parse YAML frontmatter from markdown content.

    Args:
        content: Full markdown content with frontmatter

    Returns:
        Tuple of (TestMetadata, remaining_content)

    Raises:
        YAMLValidationError: If frontmatter is missing or invalid
    """
    lines = content.strip().split("\n")

    # Check for frontmatter delimiters
    if not lines or lines[0].strip() != "---":
        raise YAMLValidationError(
            "Missing YAML frontmatter. Test files must start with '---'"
        )

    # Find closing delimiter
    try:
        end_index = lines[1:].index("---") + 1
    except ValueError:
        raise YAMLValidationError(
            "Unclosed YAML frontmatter. Missing closing '---'"
        )

    # Extract YAML and remaining content
    yaml_lines = lines[1:end_index]
    yaml_content = "\n".join(yaml_lines)
    remaining_content = "\n".join(lines[end_index + 1:])

    # Validate YAML
    metadata = validate_yaml_frontmatter(yaml_content)

    return metadata, remaining_content
