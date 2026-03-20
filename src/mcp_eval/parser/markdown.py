"""Markdown test case parser."""

import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..models import TestCase, ConversationTurn, Expectation, ExpectationType
from .yaml_validator import parse_yaml_frontmatter, YAMLValidationError

logger = logging.getLogger(__name__)


class MarkdownParseError(Exception):
    """Custom exception for markdown parsing errors."""
    pass


def expand_templates(content: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Expand template variables in content.

    Args:
        content: Content with template variables like {{variable_name}}
        context: Dictionary of variable name to value mappings

    Returns:
        Content with variables expanded
    """
    if context is None:
        context = {}

    def replace_var(match):
        var_name = match.group(1).strip()
        if var_name not in context:
            available = ', '.join(context.keys()) if context else 'none'
            raise MarkdownParseError(
                f"Template variable '{var_name}' not found in context. "
                f"Available variables: {available}"
            )
        return str(context[var_name])

    return re.sub(r'\{\{(.+?)\}\}', replace_var, content)


def extract_expectation_type(comment_line: str) -> Optional[ExpectationType]:
    """
    Extract expectation type from HTML comment.

    Args:
        comment_line: Line potentially containing <!-- type: xxx -->

    Returns:
        ExpectationType if found, None otherwise
    """
    match = re.search(r'<!--\s*type:\s*(\w+)\s*-->', comment_line)
    if match:
        type_str = match.group(1).lower()
        try:
            return ExpectationType(type_str)
        except ValueError:
            raise MarkdownParseError(
                f"Invalid expectation type '{type_str}'. "
                f"Valid types: {', '.join(t.value for t in ExpectationType)}"
            )
    return None


def extract_threshold(comment_line: str) -> Optional[float]:
    """
    Extract threshold value from HTML comment.

    Args:
        comment_line: Line potentially containing <!-- threshold: 0.8 -->

    Returns:
        Threshold value if found, None otherwise
    """
    match = re.search(r'<!--\s*threshold:\s*([\d.]+)\s*-->', comment_line)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            raise MarkdownParseError(f"Invalid threshold value: {match.group(1)}")
    return None


def parse_markdown_sections(content: str) -> Dict[str, str]:
    """
    Parse markdown content into sections based on h2 headers.

    Args:
        content: Markdown content after frontmatter

    Returns:
        Dictionary mapping section names to content
    """
    sections = {}
    current_section = None
    current_content = []

    for line in content.split("\n"):
        # Check for h2 header
        h2_match = re.match(r'^##\s+(.+)$', line)
        if h2_match:
            # Save previous section
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            # Start new section
            current_section = h2_match.group(1).strip().lower()
            current_content = []
        elif current_section:
            current_content.append(line)

    # Save last section
    if current_section:
        sections[current_section] = "\n".join(current_content).strip()

    return sections


def parse_conversation_section(content: str) -> List[ConversationTurn]:
    """
    Parse conversation section into turns.

    Supports both single prompt and multi-turn format.

    Args:
        content: Content of conversation/prompt section

    Returns:
        List of ConversationTurn objects
    """
    turns = []
    lines = content.split("\n")

    # Check if this is multi-turn (has ### User or ### Assistant)
    has_subsections = any(re.match(r'^###\s+(User|Assistant)', line, re.IGNORECASE) for line in lines)

    if not has_subsections:
        # Single turn - entire content is user message
        if content.strip():
            turns.append(ConversationTurn(
                role="user",
                content=content.strip()
            ))
    else:
        # Multi-turn conversation
        current_role = None
        current_content = []

        for line in lines:
            h3_match = re.match(r'^###\s+(User|Assistant)', line, re.IGNORECASE)
            if h3_match:
                # Save previous turn
                if current_role and current_content:
                    turns.append(ConversationTurn(
                        role=current_role.lower(),
                        content="\n".join(current_content).strip()
                    ))
                # Start new turn
                current_role = h3_match.group(1)
                current_content = []
            elif current_role:
                current_content.append(line)

        # Save last turn
        if current_role and current_content:
            turns.append(ConversationTurn(
                role=current_role.lower(),
                content="\n".join(current_content).strip()
            ))

    return turns


def parse_expectations_section(content: str) -> List[Expectation]:
    """
    Parse expectations section into Expectation objects.

    Format:
        <!-- type: regex -->
        <!-- threshold: 0.8 -->
        Expected output here

    Args:
        content: Content of expectations/expected section

    Returns:
        List of Expectation objects
    """
    expectations = []
    lines = content.split("\n")

    current_type = ExpectationType.EXACT  # default
    current_threshold = None
    current_value = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check for type comment
        exp_type = extract_expectation_type(line)
        if exp_type:
            # Save previous expectation if any
            if current_value:
                expectations.append(Expectation(
                    type=current_type,
                    value="\n".join(current_value).strip(),
                    threshold=current_threshold
                ))
                current_value = []
                current_threshold = None

            current_type = exp_type
            i += 1
            continue

        # Check for threshold comment
        threshold = extract_threshold(line)
        if threshold is not None:
            current_threshold = threshold
            i += 1
            continue

        # Regular content line
        if line.strip() or current_value:  # Include line if non-empty or we've started collecting
            current_value.append(line)

        i += 1

    # Save last expectation
    if current_value:
        expectations.append(Expectation(
            type=current_type,
            value="\n".join(current_value).strip(),
            threshold=current_threshold
        ))

    return expectations


def parse_commands_section(content: str) -> List[str]:
    """
    Parse setup or teardown section into list of commands.

    Commands can be:
    - Code blocks (```bash ... ```)
    - Bullet points
    - Plain lines

    Args:
        content: Content of setup/teardown section

    Returns:
        List of command strings
    """
    commands = []

    # Extract from code blocks
    code_blocks = re.findall(r'```(?:bash|sh)?\n(.*?)```', content, re.DOTALL)
    for block in code_blocks:
        for line in block.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                commands.append(line)

    # If no code blocks, try bullet points or plain lines
    if not commands:
        for line in content.split("\n"):
            line = line.strip()
            # Remove bullet points
            line = re.sub(r'^[-*]\s+', '', line)
            if line and not line.startswith("#"):
                commands.append(line)

    return commands


def parse_test_case(
    file_path: str,
    template_context: Optional[Dict[str, Any]] = None
) -> TestCase:
    """
    Parse a markdown test case file.

    Args:
        file_path: Path to markdown file
        template_context: Optional dictionary for template variable expansion

    Returns:
        TestCase object

    Raises:
        YAMLValidationError: If frontmatter is invalid
        MarkdownParseError: If markdown structure is invalid
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Test file not found: {file_path}")

    content = path.read_text(encoding="utf-8")

    # Expand templates if context provided
    if template_context:
        content = expand_templates(content, template_context)

    # Parse frontmatter
    try:
        metadata, body = parse_yaml_frontmatter(content)
    except YAMLValidationError as e:
        raise YAMLValidationError(f"Error parsing {file_path}: {str(e)}")

    # Parse sections
    sections = parse_markdown_sections(body)

    # Parse conversation
    conversation = []
    if "prompt" in sections:
        conversation = parse_conversation_section(sections["prompt"])
    elif "conversation" in sections:
        conversation = parse_conversation_section(sections["conversation"])
    else:
        raise MarkdownParseError(
            f"Missing required section in {file_path}. "
            "Test case must have either '## Prompt' or '## Conversation' section."
        )

    # Parse expectations
    expectations = []
    if "expected" in sections:
        expectations = parse_expectations_section(sections["expected"])
    elif "expectations" in sections:
        expectations = parse_expectations_section(sections["expectations"])

    # Parse setup/teardown
    setup_commands = []
    if "setup" in sections:
        setup_commands = parse_commands_section(sections["setup"])

    teardown_commands = []
    if "teardown" in sections:
        teardown_commands = parse_commands_section(sections["teardown"])

    return TestCase(
        metadata=metadata,
        conversation=conversation,
        expectations=expectations,
        setup_commands=setup_commands,
        teardown_commands=teardown_commands
    )


def parse_test_suite(directory: str) -> List[TestCase]:
    """
    Parse all test cases in a directory.

    Args:
        directory: Path to directory containing test markdown files

    Returns:
        List of TestCase objects
    """
    test_dir = Path(directory)
    if not test_dir.exists():
        raise FileNotFoundError(f"Test directory not found: {directory}")

    if not test_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    test_cases = []
    for md_file in test_dir.glob("*.md"):
        try:
            test_case = parse_test_case(str(md_file))
            test_cases.append(test_case)
        except (YAMLValidationError, MarkdownParseError) as e:
            logger.warning(f"Skipping {md_file.name}: {str(e)}")

    return test_cases
