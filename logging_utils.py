"""
Logging module for PDF Watermark Remover.

This module provides a centralized logging configuration for the application.
It supports logging to file and console, and allows for different log levels.

Author: PDF Watermark Remover Team
Version: 2.0.0
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

from config import Config


def setup_logging(
    level: Optional[str] = None, 
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> logging.Logger:
    """
    Set up logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        log_format: Log format string (optional)
        
    Returns:
        logging.Logger: Root logger
    """
    # Get configuration
    config = Config()
    
    # Use provided values or defaults from configuration
    level = level or config.LOG_LEVEL
    log_file = log_file or config.LOG_FILE
    log_format = log_format or config.LOG_FORMAT
    
    # Convert level string to logging level
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        print(f"Invalid log level: {level}", file=sys.stderr)
        numeric_level = logging.INFO
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if log file is specified
    if log_file:
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Create rotating file handler (max 5 MB, max 5 backup files)
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)
