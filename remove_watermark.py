"""
Core watermark removal module for PDF Watermark Remover.

This module provides the main entry point for removing watermarks from PDF files.
It uses the Strategy pattern to select the appropriate watermark removal technique
based on the characteristics of the input PDF.

Author: PDF Watermark Remover Team
Version: 2.0.0
"""

import logging
from typing import Optional, Callable, Dict, Any
from pathlib import Path
import fitz  # PyMuPDF

from config import Config
from exceptions import InvalidPDFError, PDFProcessingError
from logging_utils import get_logger
from strategies import (
    WatermarkRemovalStrategy,
    XRefImageRemovalStrategy,
    CommonStringRemovalStrategy
)


# Configure logging
logger = get_logger(__name__)


class ProgressCallback:
    """
    Progress callback for watermark removal.
    
    This class provides a consistent interface for tracking progress during
    watermark removal, with support for progress bars.
    """
    
    def __init__(
        self, 
        callback: Optional[Callable[[str, float], None]] = None,
        total_steps: int = 100
    ):
        """
        Initialize progress callback.
        
        Args:
            callback: Callback function for progress updates
            total_steps: Total number of steps for progress tracking
        """
        self.callback = callback
        self.total_steps = total_steps
        self.current_step = 0
        self.current_status = ""
    
    def update(
        self, 
        status: str = "", 
        step: Optional[int] = None,
        increment: int = 1
    ):
        """
        Update progress.
        
        Args:
            status: Status message
            step: Absolute step number (optional)
            increment: Step increment (if step is None)
        """
        # Update step
        if step is not None:
            self.current_step = step
        else:
            self.current_step += increment
        
        # Update status
        if status:
            self.current_status = status
        
        # Calculate progress percentage
        progress = self.current_step / self.total_steps
        
        # Call callback
        if self.callback:
            self.callback(self.current_status, progress)


class WatermarkRemover:
    """
    Main watermark remover class that coordinates removal strategies.
    
    This class implements the Strategy pattern, automatically selecting
    the appropriate removal strategy based on PDF characteristics.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the watermark remover.
        
        Args:
            config_file: Path to configuration file (optional)
        """
        # Load configuration
        self.config = Config(config_file)
        
        # Initialize strategies
        self.strategies = [
            XRefImageRemovalStrategy(),
            CommonStringRemovalStrategy()
        ]
        
        logger.info(
            f"Initialized WatermarkRemover with {len(self.strategies)} strategies"
        )
    
    def _select_strategy(self, doc: fitz.Document) -> WatermarkRemovalStrategy:
        """
        Select appropriate strategy based on document characteristics.
        
        Args:
            doc: PyMuPDF document object
            
        Returns:
            WatermarkRemovalStrategy: Selected strategy instance
        """
        for strategy in self.strategies:
            if strategy.can_handle(doc):
                logger.info(f"Selected strategy: {strategy.__class__.__name__}")
                return strategy
        
        # This should never happen as CommonStringRemovalStrategy handles all
        logger.error("No suitable strategy found for document")
        return self.strategies[-1]  # Fallback to the last strategy
    
    async def remove_watermark(
        self, 
        input_file: str, 
        output_file: str,
        progress_callback: Optional[Callable[[str, float], None]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Remove watermark from PDF file using appropriate strategy.
        
        Args:
            input_file: Path to input PDF file
            output_file: Path to output PDF file
            progress_callback: Optional callback for progress updates (status, progress)
            metadata: Optional metadata to add to the output PDF
            
        Returns:
            bool: True if watermark was successfully removed
            
        Raises:
            InvalidPDFError: If input file is not a valid PDF
            PDFProcessingError: If there's an error processing the PDF
        """
        input_path = Path(input_file)
        output_path = Path(output_file)
        
        # Create progress tracker
        progress = ProgressCallback(progress_callback)
        progress.update("Validating input file", 0)
        
        # Validate input file
        if not input_path.exists():
            raise InvalidPDFError(f"Input file not found: {input_file}")
        
        if not input_path.suffix.lower() == ".pdf":
            raise InvalidPDFError(f"Input file is not a PDF: {input_file}")
        
        try:
            # Open document to determine strategy
            progress.update("Analyzing PDF", 5)
            doc = fitz.open(str(input_path))
            
            # Log document metadata
            logger.info(f"Document metadata: {doc.metadata}")
            
            # Update progress
            progress.update("Selecting strategy", 10)
            
            # 按照原始代碼的邏輯來選擇策略
            if 'Version' in doc.metadata.get('producer', ''):
                logger.info("Using XRef strategy based on producer metadata")
                doc.close()
                
                # Process with XRef strategy
                progress.update("Processing with XRef strategy", 15)
                return await self.strategies[0].remove(
                    input_path, 
                    output_path, 
                    lambda s, p: progress.update(
                        s,
                        15 + int(p * 80)
                    )
                )
            else:
                logger.info("Using Common String strategy")
                doc.close()
                
                # Process with Common String strategy
                progress.update("Processing with Common String strategy", 15)
                return await self.strategies[1].remove(
                    input_path, 
                    output_path,
                    lambda s, p: progress.update(
                        s,
                        15 + int(p * 80)
                    )
                )
            
        except Exception as e:
            logger.error(f"Error removing watermark: {str(e)}")
            raise


# Convenience function for backward compatibility
async def remove_watermark(
    input_file: str, 
    output_file: str,
    progress_callback: Optional[Callable[[str, float], None]] = None,
    config_file: Optional[str] = None
) -> bool:
    """
    Remove watermark from PDF file.
    
    This is a convenience function that maintains backward compatibility
    with the original API.
    
    Args:
        input_file: Path to input PDF file
        output_file: Path to output PDF file
        progress_callback: Optional callback for progress updates
        config_file: Path to configuration file (optional)
        
    Returns:
        bool: True if watermark was successfully removed
    """
    remover = WatermarkRemover(config_file)
    return await remover.remove_watermark(
        input_file, 
        output_file,
        progress_callback
    )
