"""
Migration Reporting Service

Generates reports for migration operations.
Provides summary and detailed reporting capabilities.
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class MigrationReporter:
    """
    Migration reporting service

    Generates reports and summaries for migration operations,
    including success/failure statistics and detailed logs.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize reporter

        Args:
            output_dir: Directory for report output (default: logs/)
        """
        self.output_dir = output_dir or Path("logs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def generate_batch_report(
        self,
        batch_id: uuid.UUID,
        file_results: List[Dict[str, Any]],
        summary: Dict[str, Any]
    ) -> Path:
        """
        Generate batch migration report

        Args:
            batch_id: Batch identifier
            file_results: List of file migration results
            summary: Summary statistics

        Returns:
            Path to generated report file
        """
        report_data = {
            'batch_id': str(batch_id),
            'generated_at': datetime.now().isoformat(),
            'summary': summary,
            'file_results': file_results
        }

        report_path = self.output_dir / f"batch_report_{batch_id}.json"

        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)

        self.logger.info(f"Generated batch report: {report_path}")
        return report_path

    def generate_file_report(
        self,
        file_path: Path,
        migration_result: Dict[str, Any],
        validation_result: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Generate file migration report

        Args:
            file_path: Source file path
            migration_result: Migration results
            validation_result: Validation results (optional)

        Returns:
            Path to generated report file
        """
        report_data = {
            'file_path': str(file_path),
            'file_name': file_path.name,
            'generated_at': datetime.now().isoformat(),
            'migration_result': migration_result,
            'validation_result': validation_result
        }

        report_path = self.output_dir / f"file_report_{file_path.stem}.json"

        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)

        self.logger.info(f"Generated file report: {report_path}")
        return report_path

    def generate_summary(
        self,
        file_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate migration summary statistics

        Args:
            file_results: List of file results

        Returns:
            Summary dictionary
        """
        total_files = len(file_results)
        successful = sum(1 for r in file_results if r.get('status') == 'completed')
        failed = total_files - successful
        total_records = sum(r.get('records_processed', 0) for r in file_results)

        summary = {
            'total_files': total_files,
            'successful_migrations': successful,
            'failed_migrations': failed,
            'total_records_processed': total_records,
            'success_rate': (successful / total_files * 100) if total_files > 0 else 0
        }

        return summary
