#!/usr/bin/env python3
"""
Centralized logging configuration for OKR Project.

This module provides a standardized logging setup across all project components.
"""

import logging
import logging.handlers
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON formatted log string
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra'):
            log_entry.update(record.extra)
        
        return json.dumps(log_entry)


class OKRLogger:
    """Centralized logger configuration for OKR Project."""
    
    def __init__(self, name: str, level: str = "INFO", 
                 log_file: Optional[str] = None):
        """Initialize the logger.
        
        Args:
            name: Logger name (usually __name__)
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional log file path
        """
        self.name = name
        self.level = getattr(logging, level.upper())
        self.log_file = log_file
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup and configure the logger.
        
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(self.name)
        logger.setLevel(self.level)
        
        # Clear existing handlers to avoid duplicates
        logger.handlers.clear()
        
        # Console handler with JSON formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.level)
        console_handler.setFormatter(JSONFormatter())
        logger.addHandler(console_handler)
        
        # File handler if log file specified
        if self.log_file:
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(self.level)
            file_handler.setFormatter(JSONFormatter())
            logger.addHandler(file_handler)
        
        return logger
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance.
        
        Returns:
            Logger instance
        """
        return self.logger
    
    def log_with_context(self, level: str, message: str, 
                        context: Optional[Dict[str, Any]] = None) -> None:
        """Log message with additional context.
        
        Args:
            level: Log level
            message: Log message
            context: Additional context data
        """
        log_func = getattr(self.logger, level.lower())
        if context:
            log_func(message, extra={'context': context})
        else:
            log_func(message)


def get_logger(name: str, level: str = "INFO", 
               log_file: Optional[str] = None) -> logging.Logger:
    """Get a configured logger instance.
    
    Args:
        name: Logger name
        level: Logging level
        log_file: Optional log file path
        
    Returns:
        Configured logger instance
    """
    okr_logger = OKRLogger(name, level, log_file)
    return okr_logger.get_logger()


def setup_team_logger(team: str, component: str, 
                     level: str = "INFO") -> logging.Logger:
    """Setup logger for specific team and component.
    
    Args:
        team: Team name (ai, data, shared)
        component: Component name
        level: Logging level
        
    Returns:
        Configured logger instance
    """
    logger_name = f"okr.{team}.{component}"
    log_file = f"logs/{team}/{component}.log"
    
    return get_logger(logger_name, level, log_file)


# Pre-configured loggers for each team
class TeamLoggers:
    """Pre-configured loggers for different teams."""
    
    @staticmethod
    def ai_logger(component: str, level: str = "INFO") -> logging.Logger:
        """Get AI team logger.
        
        Args:
            component: Component name
            level: Logging level
            
        Returns:
            AI team logger
        """
        return setup_team_logger("ai", component, level)
    
    @staticmethod
    def data_logger(component: str, level: str = "INFO") -> logging.Logger:
        """Get Data team logger.
        
        Args:
            component: Component name
            level: Logging level
            
        Returns:
            Data team logger
        """
        return setup_team_logger("data", component, level)
    
    @staticmethod
    def shared_logger(component: str, level: str = "INFO") -> logging.Logger:
        """Get Shared utilities logger.
        
        Args:
            component: Component name
            level: Logging level
            
        Returns:
            Shared utilities logger
        """
        return setup_team_logger("shared", component, level)


# Example usage functions
def log_performance(logger: logging.Logger, operation: str, 
                   duration: float, **kwargs) -> None:
    """Log performance metrics.
    
    Args:
        logger: Logger instance
        operation: Operation name
        duration: Duration in seconds
        **kwargs: Additional context
    """
    context = {
        'operation': operation,
        'duration_seconds': duration,
        'performance': True,
        **kwargs
    }
    logger.info(f"Performance: {operation} completed in {duration:.3f}s", 
                extra={'context': context})


def log_error_with_context(logger: logging.Logger, error: Exception, 
                          operation: str, **kwargs) -> None:
    """Log error with additional context.
    
    Args:
        logger: Logger instance
        error: Exception that occurred
        operation: Operation that failed
        **kwargs: Additional context
    """
    context = {
        'operation': operation,
        'error_type': type(error).__name__,
        'error_message': str(error),
        **kwargs
    }
    logger.error(f"Error in {operation}: {error}", 
                 extra={'context': context}, exc_info=True)


if __name__ == "__main__":
    # Example usage
    logger = get_logger(__name__)
    
    logger.info("Testing OKR logger setup")
    
    # Test team loggers
    ai_logger = TeamLoggers.ai_logger("model_training")
    ai_logger.info("AI model training started")
    
    data_logger = TeamLoggers.data_logger("etl_pipeline")
    data_logger.info("ETL pipeline initiated")
    
    # Test performance logging
    import time
    start_time = time.time()
    time.sleep(0.1)  # Simulate work
    duration = time.time() - start_time
    log_performance(logger, "test_operation", duration, records_processed=100)
    
    # Test error logging
    try:
        raise ValueError("Test error")
    except ValueError as e:
        log_error_with_context(logger, e, "test_error_handling", user_id="test123")
    
    print("Logger testing completed!")