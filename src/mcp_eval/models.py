"""Data models for the MCP Eval Harness."""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union, Any
from datetime import datetime, timezone
from enum import Enum


class ExpectationType(str, Enum):
    """Type of expectation for test validation."""
    EXACT = "exact"
    REGEX = "regex"
    SEMANTIC = "semantic"
    CUSTOM = "custom"


class TestMetadata(BaseModel):
    """Metadata for a test case."""
    name: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    timeout: int = 30
    retries: int = 0
    critical: bool = False
    cost_threshold: Optional[float] = None


class Expectation(BaseModel):
    """Expected output for a test case."""
    type: ExpectationType
    value: str
    threshold: Optional[float] = None
    custom_function: Optional[str] = None


class ConversationTurn(BaseModel):
    """A single turn in a conversation."""
    role: str  # "user" or "assistant"
    content: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    resources: List[str] = Field(default_factory=list)


class TestCase(BaseModel):
    """A complete test case definition."""
    metadata: TestMetadata
    conversation: List[ConversationTurn]
    expectations: List[Expectation]
    setup_commands: List[str] = Field(default_factory=list)
    teardown_commands: List[str] = Field(default_factory=list)


class TokenUsage(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class PerformanceMetrics(BaseModel):
    """Performance metrics for test execution."""
    response_time_ms: int
    tool_execution_time_ms: int
    total_time_ms: int
    token_usage: TokenUsage
    estimated_cost_usd: float


class ComparisonResult(BaseModel):
    """Result of comparing actual output to expected."""
    passed: bool
    expectation_type: ExpectationType
    expected: str
    actual: str
    score: Optional[float] = None
    details: Optional[str] = None


class TestResult(BaseModel):
    """Result of a single test case execution."""
    test_name: str
    status: str  # "passed", "failed", "error", "skipped"
    comparison_results: List[ComparisonResult] = Field(default_factory=list)
    performance: Optional[PerformanceMetrics] = None
    error_message: Optional[str] = None
    execution_time: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TestSuiteResult(BaseModel):
    """Results of a test suite execution."""
    suite_name: str
    total_tests: int
    passed: int
    failed: int
    errors: int
    skipped: int
    test_results: List[TestResult]
    total_duration: float
    total_cost: Optional[float] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    git_commit: Optional[str] = None
    baseline_commit: Optional[str] = None
    regression_detected: bool = False


class MCPServerConfig(BaseModel):
    """Configuration for an MCP server."""
    name: str
    command: str
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)


class SemanticMatchConfig(BaseModel):
    """Configuration for semantic matching."""
    provider: str = "openai"
    model: str = "gpt-4"
    api_key: Optional[str] = None
    threshold: float = 0.8


class MCPEvalConfig(BaseModel):
    """Configuration for the MCP Eval Harness."""
    test_directories: List[str] = Field(default_factory=lambda: ["tests"])
    output_directory: str = "eval-results"
    log_level: str = "INFO"
    parallel_tests: int = 1
    default_timeout: int = 30
    servers: List[MCPServerConfig] = Field(default_factory=list)
    semantic_match: Optional[SemanticMatchConfig] = None
    regression_thresholds: Dict[str, float] = Field(default_factory=dict)
    baseline_strategy: str = "main_branch"  # "main_branch", "last_tag", "manual"
