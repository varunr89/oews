"""
File Discovery Service Contract

Maps to Functional Requirements:
- FR-001: System MUST discover and enumerate all Excel files (.xls, .xlsx) in specified directory locations
"""

from typing import List, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExcelFileInfo:
    """Information about a discovered Excel file"""
    file_path: Path
    file_name: str
    file_size: int
    file_hash: str
    created_at: str  # ISO format
    modified_at: str  # ISO format
    sheet_count: int


@dataclass
class DiscoveryOptions:
    """Configuration options for file discovery"""
    include_subdirectories: bool = True
    max_file_size: int = 104857600  # 100MB
    file_extensions: List[str] = None  # ['.xls', '.xlsx'] if None
    exclude_patterns: List[str] = None  # Regex patterns to exclude

    def __post_init__(self):
        if self.file_extensions is None:
            self.file_extensions = ['.xls', '.xlsx']
        if self.exclude_patterns is None:
            self.exclude_patterns = []


@dataclass
class DiscoveryResult:
    """Result of file discovery operation"""
    files_found: List[ExcelFileInfo]
    total_count: int
    total_size: int
    errors: List[str]
    discovery_duration: float  # seconds


class FileDiscoveryService(ABC):
    """Abstract interface for file discovery operations"""

    @abstractmethod
    def discover_excel_files(
        self,
        directory_path: Path,
        options: Optional[DiscoveryOptions] = None
    ) -> DiscoveryResult:
        """
        Discover all Excel files in the specified directory

        Args:
            directory_path: Root directory to search
            options: Discovery configuration options

        Returns:
            DiscoveryResult containing found files and metadata

        Raises:
            ValueError: If directory_path is invalid
            PermissionError: If directory is not accessible
        """
        pass

    @abstractmethod
    def validate_file_accessibility(self, file_path: Path) -> bool:
        """
        Check if an Excel file can be read and processed

        Args:
            file_path: Path to the Excel file

        Returns:
            True if file is accessible and valid, False otherwise
        """
        pass

    @abstractmethod
    def get_file_metadata(self, file_path: Path) -> ExcelFileInfo:
        """
        Extract metadata from an Excel file

        Args:
            file_path: Path to the Excel file

        Returns:
            ExcelFileInfo with file metadata

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file is not readable
        """
        pass

    @abstractmethod
    def watch_directory_for_changes(
        self,
        directory_path: Path,
        callback: callable
    ) -> None:
        """
        Monitor directory for new Excel files (for incremental migration)

        Args:
            directory_path: Directory to monitor
            callback: Function to call when new files are detected

        Raises:
            ValueError: If directory_path is invalid
        """
        pass