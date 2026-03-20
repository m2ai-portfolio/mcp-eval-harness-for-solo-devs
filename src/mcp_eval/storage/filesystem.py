"""File-based storage for test results."""

import json
import re
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from ..models import TestSuiteResult


class FileSystemStore:
    """Store results as JSON files on disk."""

    def __init__(self, output_dir: str = "./eval-results"):
        """
        Initialize filesystem store.

        Args:
            output_dir: Directory to store result files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_suite_result(self, result: TestSuiteResult) -> str:
        """
        Save test suite result to JSON file.

        Args:
            result: Test suite result to save

        Returns:
            Path to saved file
        """
        # Generate filename with timestamp
        timestamp = result.timestamp.strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'[^\w\-.]', '_', result.suite_name)
        filename = f"{safe_name}_{timestamp}.json"
        filepath = self.output_dir / filename

        # Save to JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            data = result.model_dump(mode='json')
            json.dump(data, f, indent=2, default=str)

        return str(filepath)

    def load_suite_result(self, filepath: str) -> TestSuiteResult:
        """
        Load test suite result from JSON file.

        Args:
            filepath: Path to JSON file

        Returns:
            TestSuiteResult loaded from file

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file contains invalid data or path is outside output_dir
        """
        file_path = Path(filepath).resolve()

        # Path traversal protection
        if not str(file_path).startswith(str(self.output_dir.resolve())):
            raise ValueError(f"Invalid file path: must be within {self.output_dir}")

        if not file_path.exists():
            raise FileNotFoundError(f"Result file not found: {filepath}")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return TestSuiteResult(**data)

    def list_results(self) -> List[str]:
        """
        List all result files in the output directory.

        Returns:
            List of absolute paths to result files, sorted by modification time (newest first)
        """
        json_files = list(self.output_dir.glob("*.json"))
        # Sort by modification time, newest first
        json_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return [str(f.absolute()) for f in json_files]

    def get_latest_result(self, suite_name_prefix: Optional[str] = None) -> Optional[str]:
        """
        Get the path to the most recent result file.

        Args:
            suite_name_prefix: Optional prefix to filter by suite name

        Returns:
            Path to most recent result file, or None if no files found
        """
        results = self.list_results()

        if not results:
            return None

        if suite_name_prefix:
            # Filter by suite name prefix
            safe_prefix = re.sub(r'[^\w\-.]', '_', suite_name_prefix)
            filtered = [r for r in results if Path(r).name.startswith(safe_prefix)]
            return filtered[0] if filtered else None

        return results[0]

    def delete_result(self, filepath: str):
        """
        Delete a result file.

        Args:
            filepath: Path to file to delete

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If path is outside output_dir
        """
        file_path = Path(filepath).resolve()

        # Path traversal protection
        if not str(file_path).startswith(str(self.output_dir.resolve())):
            raise ValueError(f"Invalid file path: must be within {self.output_dir}")

        if not file_path.exists():
            raise FileNotFoundError(f"Result file not found: {filepath}")

        file_path.unlink()

    def cleanup_old_results(self, keep_count: int = 10):
        """
        Delete old result files, keeping only the most recent ones.

        Args:
            keep_count: Number of recent files to keep
        """
        results = self.list_results()

        # Delete all except the most recent keep_count files
        for filepath in results[keep_count:]:
            Path(filepath).unlink()
