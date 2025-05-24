"""
PDF Watermark Remover - A tool for removing watermarks from PDF files.

This package provides tools for removing watermarks from PDF files, including:
- Command-line interface
- Web server interface
- Core watermark removal functionality

The package implements a Strategy pattern for handling different types of watermarks,
with specialized strategies for image-based and text-based watermarks.

Author: PDF Watermark Remover Team
Version: 2.0.0
"""

# First import config and logging as they are dependencies for other modules
from .config import Config
from .logging_utils import setup_logging, get_logger

# Set up logging
setup_logging()

# Import exceptions
from .exceptions import (
    PDFWatermarkRemoverError,
    PDFProcessingError,
    InvalidPDFError,
    WatermarkNotFoundError,
    StrategyError,
    FileOperationError,
    ConfigurationError
)

# Import strategies
from .strategies import (
    WatermarkRemovalStrategy,
    XRefImageRemovalStrategy,
    CommonStringRemovalStrategy
)

# Import core functionality
from .remove_watermark import WatermarkRemover, remove_watermark

# Package metadata
__version__ = Config().VERSION
__author__ = "PDF Watermark Remover Team"
