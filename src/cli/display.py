"""
CLI Display and Progress Utilities

Provides user feedback, progress bars, and formatted output for CLI.
"""

import click
from typing import List, Dict, Any, Optional
from datetime import datetime


class ProgressDisplay:
    """Progress display utilities for CLI operations"""

    @staticmethod
    def show_progress_bar(items: List[Any], label: str = 'Processing'):
        """
        Create a progress bar for iterating through items

        Args:
            items: List of items to process
            label: Label for the progress bar

        Returns:
            Click progress bar context manager
        """
        return click.progressbar(items, label=label, show_pos=True)

    @staticmethod
    def show_spinner(label: str = 'Processing'):
        """
        Show a spinner for indeterminate operations

        Args:
            label: Label for the spinner
        """
        click.echo(f"{label}...", nl=False)

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Format file size in human-readable format

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted string (e.g., "1.5 MB")
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

    @staticmethod
    def format_duration(seconds: float) -> str:
        """
        Format duration in human-readable format

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string (e.g., "1m 30s")
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.0f}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"

    @staticmethod
    def print_table(headers: List[str], rows: List[List[Any]]):
        """
        Print a formatted table

        Args:
            headers: List of column headers
            rows: List of row data
        """
        # Calculate column widths
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))

        # Print header
        header_row = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
        click.echo(header_row)
        click.echo("-" * len(header_row))

        # Print rows
        for row in rows:
            row_str = " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
            click.echo(row_str)

    @staticmethod
    def print_summary(title: str, data: Dict[str, Any]):
        """
        Print a formatted summary

        Args:
            title: Summary title
            data: Dictionary of key-value pairs to display
        """
        click.echo(f"\n{title}")
        click.echo("=" * len(title))

        for key, value in data.items():
            # Format key
            key_formatted = key.replace('_', ' ').title()
            click.echo(f"{key_formatted}: {value}")

    @staticmethod
    def print_success(message: str):
        """Print success message with icon"""
        click.echo(click.style(f"✓ {message}", fg='green', bold=True))

    @staticmethod
    def print_error(message: str):
        """Print error message with icon"""
        click.echo(click.style(f"✗ {message}", fg='red', bold=True), err=True)

    @staticmethod
    def print_warning(message: str):
        """Print warning message with icon"""
        click.echo(click.style(f"⚠ {message}", fg='yellow'))

    @staticmethod
    def print_info(message: str):
        """Print info message with icon"""
        click.echo(click.style(f"ℹ {message}", fg='blue'))

    @staticmethod
    def confirm_action(prompt: str, default: bool = False) -> bool:
        """
        Prompt user for confirmation

        Args:
            prompt: Confirmation prompt
            default: Default value if user just presses Enter

        Returns:
            True if confirmed, False otherwise
        """
        return click.confirm(prompt, default=default)

    @staticmethod
    def prompt_choice(prompt: str, choices: List[str]) -> str:
        """
        Prompt user to choose from options

        Args:
            prompt: Choice prompt
            choices: List of valid choices

        Returns:
            Selected choice
        """
        return click.prompt(prompt, type=click.Choice(choices))


class MigrationProgressTracker:
    """Track and display migration progress"""

    def __init__(self, total_files: int):
        """
        Initialize progress tracker

        Args:
            total_files: Total number of files to process
        """
        self.total_files = total_files
        self.completed_files = 0
        self.failed_files = 0
        self.start_time = datetime.now()

    def update(self, file_name: str, success: bool, records_processed: int = 0):
        """
        Update progress

        Args:
            file_name: Name of processed file
            success: Whether processing was successful
            records_processed: Number of records processed
        """
        if success:
            self.completed_files += 1
            status = click.style("✓", fg='green')
        else:
            self.failed_files += 1
            status = click.style("✗", fg='red')

        progress_pct = (self.completed_files + self.failed_files) / self.total_files * 100
        click.echo(f"{status} [{progress_pct:.0f}%] {file_name} ({records_processed} records)")

    def print_final_summary(self):
        """Print final summary"""
        duration = (datetime.now() - self.start_time).total_seconds()

        click.echo("\n" + "="*60)
        click.echo("Migration Summary")
        click.echo("="*60)

        click.echo(f"Total files: {self.total_files}")
        click.echo(click.style(f"Successful: {self.completed_files}", fg='green'))
        click.echo(click.style(f"Failed: {self.failed_files}", fg='red'))
        click.echo(f"Duration: {ProgressDisplay.format_duration(duration)}")

        success_rate = (self.completed_files / self.total_files * 100) if self.total_files > 0 else 0
        click.echo(f"Success rate: {success_rate:.1f}%")
