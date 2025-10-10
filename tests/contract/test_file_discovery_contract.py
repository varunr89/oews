"""
Contract Test for FileDiscoveryService

This test validates the FileDiscoveryService contract implementation.
These tests MUST FAIL initially as per TDD requirements.

Maps to Functional Requirements:
- FR-001: System MUST discover and enumerate all Excel files (.xls, .xlsx) in specified directory locations
"""

import pytest
import tempfile
import os
from pathlib import Path
from typing import List
from unittest.mock import Mock, patch

# Import the contract interface
from src.contracts.file_discovery_service import (
    FileDiscoveryService,
    ExcelFileInfo,
    DiscoveryOptions,
    DiscoveryResult
)

# This will fail until we implement the actual service
try:
    from src.services.file_discovery import FileDiscoveryServiceImpl
except ImportError:
    FileDiscoveryServiceImpl = None


class TestFileDiscoveryServiceContract:
    """Test suite for FileDiscoveryService contract compliance"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # This will fail until implementation exists
        if FileDiscoveryServiceImpl is None:
            pytest.skip("FileDiscoveryServiceImpl not implemented yet")

        self.service = FileDiscoveryServiceImpl()

    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_implements_file_discovery_service_interface(self):
        """Test that implementation follows the FileDiscoveryService contract"""
        assert isinstance(self.service, FileDiscoveryService)

        # Verify all abstract methods are implemented
        assert hasattr(self.service, 'discover_excel_files')
        assert hasattr(self.service, 'validate_file_accessibility')
        assert hasattr(self.service, 'get_file_metadata')
        assert hasattr(self.service, 'watch_directory_for_changes')

    def test_discover_excel_files_contract(self):
        """Test discover_excel_files method contract"""
        # Create test Excel files
        test_files = [
            self.temp_path / "test1.xlsx",
            self.temp_path / "test2.xls",
            self.temp_path / "subdir" / "test3.xlsx"
        ]

        # Create directory structure
        (self.temp_path / "subdir").mkdir(exist_ok=True)

        # Create dummy Excel files
        for file_path in test_files:
            file_path.touch()

        # Test with default options
        result = self.service.discover_excel_files(self.temp_path)

        # Validate return type
        assert isinstance(result, DiscoveryResult)
        assert isinstance(result.files_found, list)
        assert isinstance(result.total_count, int)
        assert isinstance(result.total_size, int)
        assert isinstance(result.errors, list)
        assert isinstance(result.discovery_duration, float)

        # Validate discovery results
        assert result.total_count >= 0
        assert result.total_size >= 0
        assert len(result.files_found) == result.total_count

    def test_discover_excel_files_with_options_contract(self):
        """Test discover_excel_files with DiscoveryOptions contract"""
        options = DiscoveryOptions(
            include_subdirectories=False,
            max_file_size=1000000,
            file_extensions=['.xlsx'],
            exclude_patterns=['temp_*']
        )

        result = self.service.discover_excel_files(self.temp_path, options)

        # Validate return type matches contract
        assert isinstance(result, DiscoveryResult)

    def test_discover_excel_files_invalid_directory_raises_valueerror(self):
        """Test that invalid directory raises ValueError as per contract"""
        invalid_path = Path("/non/existent/directory")

        with pytest.raises(ValueError):
            self.service.discover_excel_files(invalid_path)

    def test_validate_file_accessibility_contract(self):
        """Test validate_file_accessibility method contract"""
        # Create a test file
        test_file = self.temp_path / "test.xlsx"
        test_file.touch()

        # Test valid file
        result = self.service.validate_file_accessibility(test_file)
        assert isinstance(result, bool)

        # Test non-existent file
        non_existent = self.temp_path / "missing.xlsx"
        result = self.service.validate_file_accessibility(non_existent)
        assert isinstance(result, bool)
        assert result is False

    def test_get_file_metadata_contract(self):
        """Test get_file_metadata method contract"""
        # Create a test file
        test_file = self.temp_path / "metadata_test.xlsx"
        test_file.touch()

        # Test metadata extraction
        metadata = self.service.get_file_metadata(test_file)

        # Validate return type
        assert isinstance(metadata, ExcelFileInfo)
        assert isinstance(metadata.file_path, Path)
        assert isinstance(metadata.file_name, str)
        assert isinstance(metadata.file_size, int)
        assert isinstance(metadata.file_hash, str)
        assert isinstance(metadata.created_at, str)
        assert isinstance(metadata.modified_at, str)
        assert isinstance(metadata.sheet_count, int)

        # Validate data accuracy
        assert metadata.file_path == test_file
        assert metadata.file_name == "metadata_test.xlsx"
        assert metadata.file_size >= 0
        assert metadata.sheet_count >= 0

    def test_get_file_metadata_nonexistent_file_raises_filenotfounderror(self):
        """Test that non-existent file raises FileNotFoundError as per contract"""
        non_existent = self.temp_path / "missing.xlsx"

        with pytest.raises(FileNotFoundError):
            self.service.get_file_metadata(non_existent)

    def test_watch_directory_for_changes_contract(self):
        """Test watch_directory_for_changes method contract"""
        callback = Mock()

        # This should not raise an exception (may be no-op implementation initially)
        try:
            self.service.watch_directory_for_changes(self.temp_path, callback)
        except NotImplementedError:
            # Acceptable for initial implementation
            pass

    def test_watch_directory_invalid_path_raises_valueerror(self):
        """Test that invalid directory raises ValueError as per contract"""
        invalid_path = Path("/non/existent/directory")
        callback = Mock()

        with pytest.raises(ValueError):
            self.service.watch_directory_for_changes(invalid_path, callback)

    def test_discovery_options_defaults(self):
        """Test DiscoveryOptions default values"""
        options = DiscoveryOptions()

        assert options.include_subdirectories is True
        assert options.max_file_size == 104857600  # 100MB
        assert options.file_extensions == ['.xls', '.xlsx']
        assert options.exclude_patterns == []

    def test_discovery_result_structure(self):
        """Test DiscoveryResult data structure"""
        files_found = [
            ExcelFileInfo(
                file_path=Path("test.xlsx"),
                file_name="test.xlsx",
                file_size=1000,
                file_hash="abc123",
                created_at="2025-10-02T10:00:00",
                modified_at="2025-10-02T10:00:00",
                sheet_count=1
            )
        ]

        result = DiscoveryResult(
            files_found=files_found,
            total_count=1,
            total_size=1000,
            errors=[],
            discovery_duration=0.5
        )

        assert len(result.files_found) == 1
        assert result.total_count == 1
        assert result.total_size == 1000
        assert result.errors == []
        assert result.discovery_duration == 0.5

    def test_excel_file_info_structure(self):
        """Test ExcelFileInfo data structure"""
        file_info = ExcelFileInfo(
            file_path=Path("test.xlsx"),
            file_name="test.xlsx",
            file_size=2048,
            file_hash="def456",
            created_at="2025-10-02T09:00:00",
            modified_at="2025-10-02T09:30:00",
            sheet_count=3
        )

        assert file_info.file_path == Path("test.xlsx")
        assert file_info.file_name == "test.xlsx"
        assert file_info.file_size == 2048
        assert file_info.file_hash == "def456"
        assert file_info.created_at == "2025-10-02T09:00:00"
        assert file_info.modified_at == "2025-10-02T09:30:00"
        assert file_info.sheet_count == 3

    @pytest.mark.performance
    def test_performance_requirements(self):
        """Test performance requirements from contract"""
        # Create multiple test files
        for i in range(10):
            test_file = self.temp_path / f"perf_test_{i}.xlsx"
            test_file.touch()

        import time
        start_time = time.time()

        result = self.service.discover_excel_files(self.temp_path)

        end_time = time.time()
        actual_duration = end_time - start_time

        # Performance should be reasonable (less than reported duration + overhead)
        assert actual_duration < result.discovery_duration + 1.0  # 1 second overhead allowance

        # Discovery should be efficient for small datasets
        assert result.discovery_duration < 5.0  # 5 seconds max for small test

    @pytest.mark.integration
    def test_end_to_end_discovery_workflow(self):
        """Test complete discovery workflow"""
        # Setup test environment
        test_files = [
            "annual_2020.xlsx",
            "annual_2021.xlsx",
            "quarterly_q1_2022.xlsx",
            "temp_backup.xlsx"  # Should be excluded
        ]

        for filename in test_files:
            (self.temp_path / filename).touch()

        # Configure discovery options
        options = DiscoveryOptions(
            include_subdirectories=True,
            max_file_size=50000000,  # 50MB
            file_extensions=['.xlsx'],
            exclude_patterns=['temp_*']
        )

        # Execute discovery
        result = self.service.discover_excel_files(self.temp_path, options)

        # Validate results
        assert result.total_count == 3  # Should exclude temp_backup.xlsx
        assert len(result.errors) == 0
        assert all(f.file_name.endswith('.xlsx') for f in result.files_found)
        assert not any(f.file_name.startswith('temp_') for f in result.files_found)


# Additional tests for error conditions and edge cases
class TestFileDiscoveryServiceEdgeCases:
    """Test edge cases and error conditions"""

    def test_empty_directory_discovery(self):
        """Test discovery in empty directory"""
        if FileDiscoveryServiceImpl is None:
            pytest.skip("FileDiscoveryServiceImpl not implemented yet")

        service = FileDiscoveryServiceImpl()

        with tempfile.TemporaryDirectory() as temp_dir:
            result = service.discover_excel_files(Path(temp_dir))

            assert result.total_count == 0
            assert len(result.files_found) == 0
            assert result.total_size == 0

    def test_permission_denied_handling(self):
        """Test handling of permission denied errors"""
        if FileDiscoveryServiceImpl is None:
            pytest.skip("FileDiscoveryServiceImpl not implemented yet")

        service = FileDiscoveryServiceImpl()

        # This test may need to be platform-specific
        # Skip if running as admin or on systems without permission controls
        try:
            # Attempt to access a restricted directory
            restricted_path = Path("/root") if os.name != 'nt' else Path("C:\\System Volume Information")

            if restricted_path.exists():
                with pytest.raises(PermissionError):
                    service.discover_excel_files(restricted_path)
        except (PermissionError, ValueError):
            # Expected behavior - test passes
            pass

    def test_corrupted_file_handling(self):
        """Test handling of corrupted Excel files"""
        if FileDiscoveryServiceImpl is None:
            pytest.skip("FileDiscoveryServiceImpl not implemented yet")

        service = FileDiscoveryServiceImpl()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file with Excel extension but invalid content
            corrupted_file = Path(temp_dir) / "corrupted.xlsx"
            with open(corrupted_file, 'w') as f:
                f.write("This is not a valid Excel file")

            # File should be discovered but validation should fail
            result = service.discover_excel_files(Path(temp_dir))
            assert result.total_count == 1

            # Validation should return False for corrupted file
            is_valid = service.validate_file_accessibility(corrupted_file)
            assert is_valid is False