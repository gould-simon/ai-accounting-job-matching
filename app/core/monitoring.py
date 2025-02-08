"""Monitoring utilities for the application."""
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


class BotMetrics:
    """Track bot-related metrics."""
    
    def __init__(self):
        """Initialize metrics."""
        self.command_counts: Dict[str, int] = {}
        self.command_latencies: Dict[str, float] = {}
        self.error_counts: Dict[str, int] = {}
        self.last_command_time: Optional[float] = None
        self.total_updates = 0
        self.successful_updates = 0
        self.failed_updates = 0

    def track_command(self, command: str, latency: float, success: bool = True):
        """Track a bot command execution."""
        # Update command counts
        self.command_counts[command] = self.command_counts.get(command, 0) + 1
        
        # Update latencies with moving average
        current_latency = self.command_latencies.get(command, 0)
        if current_latency == 0:
            self.command_latencies[command] = latency
        else:
            # Use exponential moving average
            alpha = 0.1  # Smoothing factor
            self.command_latencies[command] = (alpha * latency) + ((1 - alpha) * current_latency)
        
        # Update last command time
        self.last_command_time = time.time()
        
        # Update success/failure counts
        self.total_updates += 1
        if success:
            self.successful_updates += 1
        else:
            self.failed_updates += 1
            self.error_counts[command] = self.error_counts.get(command, 0) + 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return {
            "total_updates": self.total_updates,
            "successful_updates": self.successful_updates,
            "failed_updates": self.failed_updates,
            "success_rate": (self.successful_updates / self.total_updates * 100) if self.total_updates > 0 else 0,
            "command_counts": self.command_counts,
            "average_latencies": self.command_latencies,
            "error_counts": self.error_counts,
            "last_command_time": self.last_command_time,
        }


# Global metrics instance
bot_metrics = BotMetrics()


def track_command_metrics(command_name: str):
    """Decorator to track bot command metrics."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                logger.error(
                    f"Error in command {command_name}",
                    extra={
                        "command": command_name,
                        "error": str(e),
                        "error_type": type(e).__name__
                    },
                    exc_info=True
                )
                raise
            finally:
                latency = time.time() - start_time
                bot_metrics.track_command(command_name, latency, success)
                
                # Log metrics
                logger.info(
                    f"Command {command_name} executed",
                    extra={
                        "command": command_name,
                        "latency": latency,
                        "success": success,
                        "total_calls": bot_metrics.command_counts.get(command_name, 0)
                    }
                )
        return wrapper
    return decorator
