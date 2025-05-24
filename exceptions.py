"""
Custom exceptions for PDF Watermark Remover.

This module defines all custom exceptions used throughout the application.
Using specific exception types allows for more precise error handling and
better diagnostics when issues occur.

Author: PDF Watermark Remover Team
Version: 2.0.0
"""


class PDFWatermarkRemoverError(Exception):
    """Base exception for all PDF Watermark Remover errors."""
    
    def __init__(self, message: str = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
        """
        self.message = message or "An error occurred in PDF Watermark Remover"
        super().__init__(self.message)


class PDFProcessingError(PDFWatermarkRemoverError):
    """
    Raised when there's an error processing a PDF file.
    
    This is a general error for PDF processing issues that don't fit into
    more specific categories.
    """
    
    def __init__(self, message: str = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
        """
        super().__init__(message or "Error processing PDF file")


class InvalidPDFError(PDFProcessingError):
    """
    Raised when an invalid PDF file is provided.
    
    This occurs when the file is not a valid PDF or is corrupted.
    """
    
    def __init__(self, message: str = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
        """
        super().__init__(message or "Invalid PDF file")


class WatermarkNotFoundError(PDFProcessingError):
    """
    Raised when no watermark pattern is found in the document.
    
    This occurs when the document doesn't contain any recognizable watermark patterns.
    """
    
    def __init__(self, message: str = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
        """
        super().__init__(message or "No watermark pattern found in document")


class StrategyError(PDFProcessingError):
    """
    Raised when there's an error with a watermark removal strategy.
    
    This occurs when a strategy fails to remove a watermark or encounters
    an error during processing.
    """
    
    def __init__(self, message: str = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
        """
        super().__init__(message or "Error in watermark removal strategy")


class FileOperationError(PDFWatermarkRemoverError):
    """
    Raised when there's an error performing file operations.
    
    This occurs when there's an issue reading, writing, or manipulating files.
    """
    
    def __init__(self, message: str = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
        """
        super().__init__(message or "Error performing file operation")


class ConfigurationError(PDFWatermarkRemoverError):
    """
    Raised when there's an error with the configuration.
    
    This occurs when there's an issue with the application configuration,
    such as invalid settings or missing required values.
    """
    
    def __init__(self, message: str = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
        """
        super().__init__(message or "Error in configuration")
