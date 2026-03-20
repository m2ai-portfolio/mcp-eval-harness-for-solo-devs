"""Storage and persistence for test results."""

from .sqlite import SQLiteStore
from .filesystem import FileSystemStore

__all__ = [
    'SQLiteStore',
    'FileSystemStore',
]
