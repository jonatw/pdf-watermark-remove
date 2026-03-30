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
    OCGWatermarkRemovalStrategy,
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

        # Initialize strategies (priority order: XRef > OCG > CommonString)
        self.strategies = [
            XRefImageRemovalStrategy(),
            OCGWatermarkRemovalStrategy(),
            CommonStringRemovalStrategy()
        ]

        logger.info(
            f"Initialized WatermarkRemover with {len(self.strategies)} strategies"
        )

    def _is_rasterized_only(self, doc: fitz.Document) -> bool:
        """
        Check if PDF is a rasterized-only document (e.g. browser print-to-PDF).

        A rasterized-only PDF has every page as a single image with no text
        operators in the content stream. Watermarks in such PDFs are baked
        into image pixels and cannot be removed by PDF stream manipulation.

        Args:
            doc: PyMuPDF document object

        Returns:
            bool: True if all pages are rasterized-only images
        """
        if len(doc) == 0:
            return False

        for page in doc:
            images = page.get_images(full=True)
            if len(images) != 1:
                return False
            if page.get_text("text").strip():
                return False
            for xref in page.get_contents():
                stream = doc.xref_stream(xref).decode("latin1")
                if "BT" in stream or "Tj" in stream or "TJ" in stream:
                    return False
        return True

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

            # Check if PDF is rasterized-only (e.g. browser print-to-PDF)
            if self._is_rasterized_only(doc):
                doc.close()
                logger.warning(
                    "PDF appears to be a rasterized image (e.g. browser print-to-PDF). "
                    "Watermarks embedded in image pixels cannot be removed. "
                    "Please use one of these methods to obtain a processable PDF:\n"
                    "  - Download from iPad app (image-based watermark, removable)\n"
                    "  - Download from website (text-based watermark, removable)\n"
                    "  - Do NOT use browser print/save-as-PDF"
                )
                return False

            # Update progress
            progress.update("Selecting strategy", 10)

            # Select strategy: XRef > OCG > CommonString
            if 'Version' in doc.metadata.get('producer', ''):
                logger.info("Using XRef strategy based on producer metadata")
                strategy = self.strategies[0]
                strategy_name = "XRef"
            elif self.strategies[1].can_handle(doc):
                logger.info("Using OCG Watermark layer strategy")
                strategy = self.strategies[1]
                strategy_name = "OCG Watermark"
            else:
                logger.info("Using Common String strategy")
                strategy = self.strategies[2]
                strategy_name = "Common String"

            doc.close()

            progress.update(f"Processing with {strategy_name} strategy", 15)
            return await strategy.remove(
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
