"""Configuration management for MCP Eval Harness."""

import os
import yaml
from pathlib import Path
from typing import Optional
from .models import MCPEvalConfig


class ConfigError(Exception):
    """Custom exception for configuration errors."""
    pass


def load_config(config_path: Optional[str] = None) -> MCPEvalConfig:
    """
    Load configuration from YAML file.

    Supports environment variable overrides:
    - MCP_EVAL_CONFIG_PATH: Path to config file
    - MCP_EVAL_OUTPUT_DIR: Override output_directory
    - MCP_EVAL_LOG_LEVEL: Override log_level
    - MCP_EVAL_PARALLEL: Override parallel_tests

    Args:
        config_path: Path to config file (default: ./mcp-eval.yaml)

    Returns:
        MCPEvalConfig object

    Raises:
        ConfigError: If config file is invalid
    """
    # Determine config file path
    if config_path is None:
        config_path = os.environ.get("MCP_EVAL_CONFIG_PATH", "./mcp-eval.yaml")

    path = Path(config_path)

    # If config file doesn't exist, use defaults
    if not path.exists():
        config_data = {}
    else:
        try:
            with open(path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in config file {config_path}: {str(e)}")
        except Exception as e:
            raise ConfigError(f"Error reading config file {config_path}: {str(e)}")

    # Apply environment variable overrides
    if "MCP_EVAL_OUTPUT_DIR" in os.environ:
        config_data["output_directory"] = os.environ["MCP_EVAL_OUTPUT_DIR"]

    if "MCP_EVAL_LOG_LEVEL" in os.environ:
        config_data["log_level"] = os.environ["MCP_EVAL_LOG_LEVEL"]

    if "MCP_EVAL_PARALLEL" in os.environ:
        try:
            config_data["parallel_tests"] = int(os.environ["MCP_EVAL_PARALLEL"])
        except ValueError:
            raise ConfigError(
                f"Invalid MCP_EVAL_PARALLEL value: {os.environ['MCP_EVAL_PARALLEL']}"
            )

    # Validate with Pydantic
    try:
        config = MCPEvalConfig(**config_data)
    except Exception as e:
        raise ConfigError(f"Invalid configuration: {str(e)}")

    return config


def save_config(config: MCPEvalConfig, config_path: str = "./mcp-eval.yaml"):
    """
    Save configuration to YAML file.

    Args:
        config: MCPEvalConfig object
        config_path: Path to save config file
    """
    path = Path(config_path)

    # Convert to dict
    config_dict = config.model_dump(exclude_none=True)

    # Write YAML
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
