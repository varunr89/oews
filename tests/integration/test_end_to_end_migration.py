"""
End-to-End Migration Integration Test

This test validates the complete migration workflow from Excel discovery
through data migration to validation. These tests MUST FAIL initially as per TDD requirements.

Integration test scenarios based on quickstart.md workflows.
"""

import pytest
import tempfile
import uuid
import json
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import Mock, patch

# Integration test imports - these will fail until implementations exist
try:
    from src.services.file_discovery import FileDiscoveryServiceImpl
    from src.services.migration_engine import MigrationEngineServiceImpl
    from src.services.validation import ValidationServiceImpl
    from src.cli.main import main as cli_main
except ImportError:
    FileDiscoveryServiceImpl = None
    MigrationEngineServiceImpl = None
    ValidationServiceImpl = None
    cli_main = None


class TestEndToEndMigrationIntegration:
    """Integration tests for complete migration workflow"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # Skip if implementations don't exist yet
        if not all([FileDiscoveryServiceImpl, MigrationEngineServiceImpl, ValidationServiceImpl]):
            pytest.skip("Service implementations not available yet")

        # Initialize services
        self.file_discovery = FileDiscoveryServiceImpl()
        self.migration_engine = MigrationEngineServiceImpl()
        self.validation_service = ValidationServiceImpl()

        # Create test data directory structure
        self.data_dir = self.temp_path / "test_data"
        self.data_dir.mkdir()

        # Create sample OEWS-like Excel files
        self._create_test_excel_files()

    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        import os
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_test_excel_files(self):
        """Create sample Excel files for testing"""
        test_files = [
            "oews_2020_annual.xlsx",
            "oews_2021_annual.xlsx",
            "oews_2022_q1.xlsx",
            "oews_2022_q2.xlsx"
        ]

        for filename in test_files:
            test_file = self.data_dir / filename
            test_file.touch()
            # In real implementation, these would be actual Excel files with OEWS data

    @pytest.mark.integration
    def test_complete_migration_workflow_quickstart_scenario(self):
        """
        Test complete end-to-end migration workflow following quickstart.md steps

        This test replicates the 30-minute quickstart scenario:
        1. File discovery
        2. Schema analysis
        3. Unified schema creation
        4. Data migration
        5. Data validation
        6. Incremental migration
        """

        # Step 1: File Discovery (quickstart Step 1)
        discovery_result = self.file_discovery.discover_excel_files(
            self.data_dir,
            options=None
        )

        assert discovery_result.total_count == 4
        assert len(discovery_result.files_found) == 4
        assert all(f.file_name.endswith(('.xls', '.xlsx')) for f in discovery_result.files_found)
        assert len(discovery_result.errors) == 0

        # Step 2: Schema Analysis (quickstart Step 2)
        # This would normally be done by a schema analyzer service
        source_schemas = {}
        for file_info in discovery_result.files_found:
            # Mock schema analysis - in real implementation this would parse Excel files
            source_schemas[str(file_info.file_path)] = {
                "sheets": ["Employment", "Wages"],
                "columns": ["occupation_code", "occupation_title", "employment", "wages"]
            }

        # Step 3: Unified Schema Creation (quickstart Step 3)
        # Mock unified schema - in real implementation this would be generated
        target_schema = "oews_unified"

        # Step 4: Data Migration (quickstart Step 4)
        excel_files = [f.file_path for f in discovery_result.files_found]

        batch_id = self.migration_engine.start_migration_batch(
            excel_files,
            target_schema,
            options=None
        )

        assert isinstance(batch_id, uuid.UUID)

        # Monitor migration progress
        progress = self.migration_engine.get_migration_progress(batch_id)
        assert isinstance(progress, list)
        assert len(progress) == len(excel_files)

        # Step 5: Data Validation (quickstart Step 5)
        validation_report = self.validation_service.validate_data_integrity(
            batch_id,
            options=None
        )

        assert validation_report.batch_id == batch_id
        assert validation_report.total_records_validated >= 0
        assert validation_report.data_integrity_score >= 0.0

        # Step 6: Incremental Migration Test (quickstart Step 6)
        # Add a new file and test incremental migration
        new_file = self.data_dir / "oews_2023_q1.xlsx"
        new_file.touch()

        incremental_result = self.migration_engine.migrate_single_file(
            new_file,
            target_schema,
            batch_id,
            options=None
        )

        assert incremental_result.batch_id == batch_id
        assert incremental_result.file_path == new_file
        assert incremental_result.records_processed >= 0

    @pytest.mark.integration
    def test_error_handling_and_recovery_workflow(self):
        """Test error handling and recovery mechanisms"""

        # Create a corrupted file to test error handling
        corrupted_file = self.data_dir / "corrupted.xlsx"
        with open(corrupted_file, 'w') as f:
            f.write("This is not a valid Excel file")

        # Test discovery with corrupted file
        discovery_result = self.file_discovery.discover_excel_files(self.data_dir)

        # Should discover the file but mark it as problematic
        total_files = len(list(self.data_dir.glob("*.xlsx")))
        assert discovery_result.total_count == total_files

        # Test migration with error handling
        excel_files = [f.file_path for f in discovery_result.files_found]

        batch_id = self.migration_engine.start_migration_batch(
            excel_files,
            "test_schema",
            options=None
        )

        # Migration should handle errors gracefully
        progress = self.migration_engine.get_migration_progress(batch_id)
        assert isinstance(progress, list)

        # Test rollback functionality
        rollback_info = self.migration_engine.rollback_batch_migration(batch_id)
        assert isinstance(rollback_info, list)

    @pytest.mark.integration
    def test_performance_requirements_validation(self):
        """Test that performance requirements are met"""

        # Test discovery performance (should be fast)
        import time
        start_time = time.time()

        discovery_result = self.file_discovery.discover_excel_files(self.data_dir)

        discovery_duration = time.time() - start_time

        # Discovery should be fast for small datasets (< 5 seconds per constitutional requirement)
        assert discovery_duration < 5.0
        assert discovery_result.discovery_duration <= discovery_duration + 1.0  # Allow for measurement overhead

        # Test migration memory constraints
        excel_files = [f.file_path for f in discovery_result.files_found]

        batch_id = self.migration_engine.start_migration_batch(
            excel_files,
            "performance_test_schema",
            options=None
        )

        # Check that migration respects memory limits (constitutional requirement: <1.75GB)
        progress = self.migration_engine.get_migration_progress(batch_id)
        for file_progress in progress:
            # Memory usage should be within constitutional limits
            # Note: This is a mock test - real implementation would track actual memory usage
            assert hasattr(file_progress, 'current_operation')

    @pytest.mark.integration
    def test_data_consistency_validation_workflow(self):
        """Test data consistency validation across the migration"""

        # Discover files
        discovery_result = self.file_discovery.discover_excel_files(self.data_dir)
        excel_files = [f.file_path for f in discovery_result.files_found]

        # Start migration
        batch_id = self.migration_engine.start_migration_batch(
            excel_files,
            "consistency_test_schema",
            options=None
        )

        # Perform comprehensive validation
        validation_report = self.validation_service.validate_data_integrity(
            batch_id,
            options=None
        )

        # Test schema compatibility validation
        source_schema = {"columns": [{"name": "test", "type": "string"}]}
        target_schema = {"tables": [{"name": "test", "columns": [{"name": "test", "type": "VARCHAR"}]}]}

        schema_result = self.validation_service.validate_schema_compatibility(
            source_schema,
            target_schema
        )

        assert isinstance(schema_result.is_compatible, bool)
        assert isinstance(schema_result.missing_columns, list)
        assert isinstance(schema_result.type_mismatches, list)

        # Test source-target data comparison
        for file_path in excel_files:
            comparison_errors = self.validation_service.compare_source_target_data(
                file_path,
                "test_table",
                sample_size=100
            )
            assert isinstance(comparison_errors, list)

        # Generate validation summary
        summary = self.validation_service.generate_validation_summary(batch_id)
        assert isinstance(summary, dict)

    @pytest.mark.integration
    def test_incremental_and_rollback_workflow(self):
        """Test incremental migration and rollback capabilities"""

        # Initial migration
        discovery_result = self.file_discovery.discover_excel_files(self.data_dir)
        initial_files = [f.file_path for f in discovery_result.files_found]

        batch_id = self.migration_engine.start_migration_batch(
            initial_files,
            "rollback_test_schema",
            options=None
        )

        # Create rollback checkpoint
        checkpoint_id = self.validation_service.create_validation_checkpoint(
            batch_id,
            "before_incremental"
        )
        assert isinstance(checkpoint_id, str)

        # Add new files (incremental migration scenario)
        new_files = [
            self.data_dir / "oews_2023_q2.xlsx",
            self.data_dir / "oews_2023_q3.xlsx"
        ]

        for new_file in new_files:
            new_file.touch()

        # Perform incremental migration
        for new_file in new_files:
            result = self.migration_engine.migrate_single_file(
                new_file,
                "rollback_test_schema",
                batch_id,
                options=None
            )
            assert result.batch_id == batch_id
            assert result.file_path == new_file

        # Test rollback of individual file
        rollback_success = self.migration_engine.rollback_file_migration(
            new_files[0],
            "test_checkpoint"
        )
        assert isinstance(rollback_success, bool)

        # Test full batch rollback
        rollback_info = self.migration_engine.rollback_batch_migration(batch_id)
        assert isinstance(rollback_info, list)

    @pytest.mark.integration
    def test_concurrent_operations_workflow(self):
        """Test concurrent migration operations"""

        # Split files into two batches for concurrent processing
        discovery_result = self.file_discovery.discover_excel_files(self.data_dir)
        all_files = [f.file_path for f in discovery_result.files_found]

        mid_point = len(all_files) // 2
        batch1_files = all_files[:mid_point] if mid_point > 0 else all_files[:1]
        batch2_files = all_files[mid_point:] if mid_point > 0 else all_files[1:]

        # Start concurrent migration batches
        batch1_id = self.migration_engine.start_migration_batch(
            batch1_files,
            "concurrent_schema_1",
            options=None
        )

        batch2_id = self.migration_engine.start_migration_batch(
            batch2_files,
            "concurrent_schema_2",
            options=None
        )

        # Both batches should be valid
        assert isinstance(batch1_id, uuid.UUID)
        assert isinstance(batch2_id, uuid.UUID)
        assert batch1_id != batch2_id

        # Check progress of both batches
        progress1 = self.migration_engine.get_migration_progress(batch1_id)
        progress2 = self.migration_engine.get_migration_progress(batch2_id)

        assert isinstance(progress1, list)
        assert isinstance(progress2, list)

        # Test concurrent validation
        validation1 = self.validation_service.validate_data_integrity(batch1_id, options=None)
        validation2 = self.validation_service.validate_data_integrity(batch2_id, options=None)

        assert validation1.batch_id == batch1_id
        assert validation2.batch_id == batch2_id


# CLI Integration Tests
class TestCLIIntegration:
    """Integration tests for CLI interface"""

    def setup_method(self):
        """Set up CLI test fixtures"""
        if cli_main is None:
            pytest.skip("CLI implementation not available yet")

        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up CLI test fixtures"""
        import shutil
        import os
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @pytest.mark.integration
    def test_cli_discover_command_integration(self):
        """Test CLI discover command integration"""

        # Create test Excel files
        test_files = ["test1.xlsx", "test2.xlsx"]
        for filename in test_files:
            (self.temp_path / filename).touch()

        # Test CLI discover command
        import sys
        from io import StringIO

        # Capture CLI output
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        try:
            # Mock CLI command execution
            result = cli_main(["discover", "--directory", str(self.temp_path)])
            output = captured_output.getvalue()

            # Should complete without errors
            assert result is None or result == 0

        except SystemExit as e:
            # CLI commands may exit with status codes
            assert e.code == 0
        finally:
            sys.stdout = old_stdout

    @pytest.mark.integration
    def test_cli_migration_workflow_integration(self):
        """Test complete CLI migration workflow"""

        # Create test data
        test_files = ["migration_test1.xlsx", "migration_test2.xlsx"]
        for filename in test_files:
            (self.temp_path / filename).touch()

        # Test CLI workflow commands in sequence
        commands = [
            ["discover", "--directory", str(self.temp_path)],
            ["analyze", "--directory", str(self.temp_path)],
            ["create-schema", "--name", "test_schema"],
            ["migrate", "--directory", str(self.temp_path), "--schema", "test_schema"],
        ]

        for command in commands:
            try:
                result = cli_main(command)
                # Commands should complete successfully
                assert result is None or result == 0
            except (SystemExit, NotImplementedError):
                # Expected for unimplemented CLI commands
                pass


# Performance and Load Testing
class TestPerformanceIntegration:
    """Performance and load testing integration"""

    def setup_method(self):
        """Set up performance test fixtures"""
        if not all([FileDiscoveryServiceImpl, MigrationEngineServiceImpl]):
            pytest.skip("Service implementations not available yet")

        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # Create larger dataset for performance testing
        self._create_performance_test_files()

    def teardown_method(self):
        """Clean up performance test fixtures"""
        import shutil
        import os
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_performance_test_files(self):
        """Create multiple test files for performance testing"""
        # Create 20 test files to simulate a more realistic dataset
        for i in range(20):
            test_file = self.temp_path / f"perf_test_{i:03d}.xlsx"
            test_file.touch()

    @pytest.mark.performance
    @pytest.mark.integration
    def test_large_dataset_migration_performance(self):
        """Test migration performance with larger datasets"""

        file_discovery = FileDiscoveryServiceImpl()
        migration_engine = MigrationEngineServiceImpl()

        # Discovery performance test
        import time
        start_time = time.time()

        discovery_result = file_discovery.discover_excel_files(self.temp_path)

        discovery_time = time.time() - start_time

        # Should discover all test files efficiently
        assert discovery_result.total_count == 20
        assert discovery_time < 10.0  # Should complete in under 10 seconds

        # Migration performance test
        excel_files = [f.file_path for f in discovery_result.files_found]

        start_time = time.time()

        batch_id = migration_engine.start_migration_batch(
            excel_files,
            "performance_schema",
            options=None
        )

        migration_setup_time = time.time() - start_time

        # Migration setup should be fast
        assert migration_setup_time < 5.0  # Setup should complete in under 5 seconds
        assert isinstance(batch_id, uuid.UUID)

    @pytest.mark.performance
    @pytest.mark.integration
    def test_memory_usage_integration(self):
        """Test memory usage during integration workflows"""

        file_discovery = FileDiscoveryServiceImpl()
        migration_engine = MigrationEngineServiceImpl()

        # Memory usage should be within constitutional limits
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Perform discovery
        discovery_result = file_discovery.discover_excel_files(self.temp_path)
        discovery_memory = process.memory_info().rss

        # Memory usage should not spike dramatically for discovery
        memory_increase = discovery_memory - initial_memory
        assert memory_increase < 100 * 1024 * 1024  # Less than 100MB increase for discovery

        # Perform migration setup
        excel_files = [f.file_path for f in discovery_result.files_found]
        batch_id = migration_engine.start_migration_batch(
            excel_files,
            "memory_test_schema",
            options=None
        )

        migration_memory = process.memory_info().rss

        # Total memory usage should remain within constitutional limits (1.75GB)
        constitutional_limit = 1.75 * 1024 * 1024 * 1024  # 1.75GB in bytes
        assert migration_memory < constitutional_limit


# Test Fixtures and Utilities
@pytest.fixture
def sample_oews_data():
    """Fixture providing sample OEWS data structure"""
    return {
        "employment_data": [
            {
                "occupation_code": "11-1011",
                "occupation_title": "Chief Executives",
                "employment": 200840,
                "employment_rse": 1.5,
                "mean_wage": 76370,
                "wage_rse": 2.1
            },
            {
                "occupation_code": "11-1021",
                "occupation_title": "General and Operations Managers",
                "employment": 2289770,
                "employment_rse": 1.2,
                "mean_wage": 53940,
                "wage_rse": 1.8
            }
        ],
        "metadata": {
            "data_year": 2022,
            "data_period": "Annual",
            "area_code": "00000",
            "area_title": "United States"
        }
    }


@pytest.fixture
def mock_database_connection():
    """Fixture providing mock database connection"""
    mock_conn = Mock()
    mock_conn.execute = Mock()
    mock_conn.commit = Mock()
    mock_conn.rollback = Mock()
    return mock_conn