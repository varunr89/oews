"""
Performance Monitoring and Memory Management

Monitors resource usage and enforces constitutional performance requirements.
"""

import logging
import psutil
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""
    timestamp: float
    memory_used_mb: float
    memory_percent: float
    cpu_percent: float
    duration_seconds: Optional[float] = None


class PerformanceMonitor:
    """
    Performance monitoring and memory management

    Tracks resource usage and enforces constitutional limits:
    - Memory usage < 1.75GB
    - Database queries < 1 second
    - Application startup < 5 seconds
    """

    # Constitutional limits
    MAX_MEMORY_MB = 1792  # 1.75 GB in MB
    MAX_QUERY_TIME_SECONDS = 1.0
    MAX_STARTUP_TIME_SECONDS = 5.0

    def __init__(self, enable_monitoring: bool = True):
        """
        Initialize performance monitor

        Args:
            enable_monitoring: Whether to enable continuous monitoring
        """
        self.enable_monitoring = enable_monitoring
        self.process = psutil.Process()
        self.metrics_history: list[PerformanceMetrics] = []
        self.logger = logging.getLogger(__name__)

    def get_current_metrics(self) -> PerformanceMetrics:
        """
        Get current performance metrics

        Returns:
            Current performance metrics
        """
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB

        metrics = PerformanceMetrics(
            timestamp=time.time(),
            memory_used_mb=memory_mb,
            memory_percent=self.process.memory_percent(),
            cpu_percent=self.process.cpu_percent(interval=0.1)
        )

        if self.enable_monitoring:
            self.metrics_history.append(metrics)

        return metrics

    def check_memory_limit(self) -> bool:
        """
        Check if memory usage is within constitutional limit

        Returns:
            True if within limit, False otherwise
        """
        metrics = self.get_current_metrics()

        if metrics.memory_used_mb > self.MAX_MEMORY_MB:
            self.logger.warning(
                f"Memory limit exceeded: {metrics.memory_used_mb:.2f} MB > "
                f"{self.MAX_MEMORY_MB} MB (constitutional limit)"
            )
            return False

        return True

    def get_memory_usage_mb(self) -> float:
        """
        Get current memory usage in MB

        Returns:
            Memory usage in megabytes
        """
        return self.get_current_metrics().memory_used_mb

    def get_peak_memory_mb(self) -> float:
        """
        Get peak memory usage from history

        Returns:
            Peak memory usage in megabytes
        """
        if not self.metrics_history:
            return self.get_memory_usage_mb()

        return max(m.memory_used_mb for m in self.metrics_history)

    @contextmanager
    def monitor_operation(self, operation_name: str):
        """
        Context manager to monitor an operation's performance

        Args:
            operation_name: Name of the operation being monitored

        Yields:
            Performance metrics at start
        """
        start_time = time.time()
        start_metrics = self.get_current_metrics()

        self.logger.debug(
            f"Starting operation '{operation_name}' - "
            f"Memory: {start_metrics.memory_used_mb:.2f} MB"
        )

        try:
            yield start_metrics
        finally:
            end_time = time.time()
            end_metrics = self.get_current_metrics()
            duration = end_time - start_time

            end_metrics.duration_seconds = duration

            self.logger.info(
                f"Operation '{operation_name}' completed - "
                f"Duration: {duration:.2f}s, "
                f"Memory: {end_metrics.memory_used_mb:.2f} MB"
            )

            # Check constitutional limits
            if duration > self.MAX_QUERY_TIME_SECONDS and 'query' in operation_name.lower():
                self.logger.warning(
                    f"Query exceeded constitutional limit: {duration:.2f}s > "
                    f"{self.MAX_QUERY_TIME_SECONDS}s"
                )

            if not self.check_memory_limit():
                self.logger.error("Memory limit exceeded during operation")

    @contextmanager
    def enforce_memory_limit(self, limit_mb: Optional[float] = None):
        """
        Context manager to enforce memory limit

        Args:
            limit_mb: Memory limit in MB (defaults to constitutional limit)

        Raises:
            MemoryError: If memory limit is exceeded

        Yields:
            None
        """
        limit = limit_mb or self.MAX_MEMORY_MB
        start_memory = self.get_memory_usage_mb()

        try:
            yield
        finally:
            current_memory = self.get_memory_usage_mb()

            if current_memory > limit:
                raise MemoryError(
                    f"Memory limit exceeded: {current_memory:.2f} MB > {limit} MB"
                )

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary from metrics history

        Returns:
            Dictionary with performance summary
        """
        if not self.metrics_history:
            current = self.get_current_metrics()
            return {
                'current_memory_mb': current.memory_used_mb,
                'peak_memory_mb': current.memory_used_mb,
                'avg_cpu_percent': current.cpu_percent,
                'samples_count': 1
            }

        memory_values = [m.memory_used_mb for m in self.metrics_history]
        cpu_values = [m.cpu_percent for m in self.metrics_history]

        return {
            'current_memory_mb': self.get_memory_usage_mb(),
            'peak_memory_mb': max(memory_values),
            'avg_memory_mb': sum(memory_values) / len(memory_values),
            'min_memory_mb': min(memory_values),
            'avg_cpu_percent': sum(cpu_values) / len(cpu_values),
            'samples_count': len(self.metrics_history)
        }

    def clear_history(self):
        """Clear metrics history"""
        self.metrics_history.clear()
        self.logger.debug("Cleared performance metrics history")

    def log_performance_report(self):
        """Log performance summary report"""
        summary = self.get_performance_summary()

        self.logger.info("=== Performance Report ===")
        self.logger.info(f"Current Memory: {summary['current_memory_mb']:.2f} MB")
        self.logger.info(f"Peak Memory: {summary['peak_memory_mb']:.2f} MB")

        if 'avg_memory_mb' in summary:
            self.logger.info(f"Average Memory: {summary['avg_memory_mb']:.2f} MB")

        self.logger.info(f"Average CPU: {summary['avg_cpu_percent']:.1f}%")
        self.logger.info(f"Samples: {summary['samples_count']}")

        # Check constitutional compliance
        if summary['peak_memory_mb'] > self.MAX_MEMORY_MB:
            self.logger.warning(
                f"⚠️  Constitutional memory limit exceeded: "
                f"{summary['peak_memory_mb']:.2f} MB > {self.MAX_MEMORY_MB} MB"
            )
        else:
            self.logger.info(
                f"✓ Memory usage within constitutional limit "
                f"({self.MAX_MEMORY_MB} MB)"
            )


# Global performance monitor instance
performance_monitor = PerformanceMonitor()
