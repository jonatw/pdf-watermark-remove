"""
Core watermark removal module for PDF Watermark Remover.

This module provides the main entry point for removing watermarks from PDF files.
It uses the Strategy pattern to select the appropriate watermark removal technique
based on the characteristics of the input PDF.

Author: PDF Watermark Remover Team
Version: 2.0.0
"""

import re
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

    def __init__(self):
        """Initialize the watermark remover."""
        self.config = Config()

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

    @staticmethod
    def _generalize_date(date_str: str) -> str:
        """Truncate a PDF date to year-month, zeroing day/time/timezone."""
        if date_str and date_str.startswith("D:") and len(date_str) >= 8:
            year_month = date_str[2:8]
            return f"D:{year_month}01000000+00'00'"
        return ""

    @staticmethod
    def _generalize_producer(producer: str) -> str:
        """Strip version numbers, build info, and URLs from producer string."""
        if not producer:
            return ""
        cleaned = re.sub(r'\s*\(.*?\)', '', producer)
        cleaned = re.sub(r'iOS Version\s+[\d.]+\s*', '', cleaned)
        cleaned = re.sub(r'\s+[mv]?[\d][\d.\-]+\S*', '', cleaned)
        cleaned = re.sub(r'\s*Original:.*', '', cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip()
        return cleaned or "PDF Producer"

    @staticmethod
    def _strip_pdf_ids(file_path: Path):
        """Remove all /ID arrays from PDF trailer bytes."""
        try:
            with open(str(file_path), 'rb') as f:
                data = f.read()
            pattern = rb'/ID\s*\[<[0-9A-Fa-f]+><[0-9A-Fa-f]+>\]'
            new_data = re.sub(pattern, b'', data)
            if new_data != data:
                with open(str(file_path), 'wb') as f:
                    f.write(new_data)
                logger.debug("Stripped PDF /ID arrays")
        except Exception as e:
            logger.warning("Could not strip PDF /ID: %s", e)

    def _sanitize_metadata(self, file_path: Path):
        """
        Generalize metadata in a processed PDF to prevent tracking.

        Truncates dates to year-month, strips producer version info,
        clears author/creator, and removes XMP metadata entirely.
        """
        try:
            doc = fitz.open(str(file_path))
            meta = doc.metadata

            new_meta = {
                "title": meta.get("title", ""),
                "author": "",
                "subject": meta.get("subject", ""),
                "keywords": meta.get("keywords", ""),
                "creator": "",
                "producer": self._generalize_producer(meta.get("producer", "")),
                "creationDate": self._generalize_date(meta.get("creationDate", "")),
                "modDate": self._generalize_date(meta.get("modDate", "")),
            }

            doc.set_metadata(new_meta)
            doc.set_xml_metadata("")
            doc.saveIncr()
            doc.close()

            # Strip PDF /ID array from trailer (PyMuPDF always writes it on save)
            self._strip_pdf_ids(file_path)

            logger.info("Metadata sanitized: dates truncated, XMP cleared, producer generalized, /ID stripped")
        except Exception as e:
            logger.warning("Could not sanitize metadata: %s", e)

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
                logger.info("Selected strategy: %s", strategy.__class__.__name__)
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
            # Open document once — passed to strategy, closed here
            progress.update("Analyzing PDF", 5)
            doc = fitz.open(str(input_path))
            logger.info("Document metadata: %s", doc.metadata)

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

            # Select strategy via can_handle() chain: XRef > OCG > CommonString
            progress.update("Selecting strategy", 10)
            strategy = self._select_strategy(doc)
            strategy_name = strategy.__class__.__name__

            progress.update("Processing with %s strategy" % strategy_name, 15)
            result = await strategy.remove(
                doc,
                output_path,
                lambda s, p: progress.update(
                    s,
                    15 + int(p * 75)
                )
            )

            doc.close()

            if result:
                progress.update("Sanitizing metadata", 93)
                self._sanitize_metadata(output_path)
                progress.update("Complete", 95)

            return result

        except Exception as e:
            logger.error("Error removing watermark: %s", e)
            raise

# Convenience function for backward compatibility
async def remove_watermark(
    input_file: str,
    output_file: str,
    progress_callback: Optional[Callable[[str, float], None]] = None,
) -> bool:
    """
    Remove watermark from PDF file.

    Args:
        input_file: Path to input PDF file
        output_file: Path to output PDF file
        progress_callback: Optional callback for progress updates

    Returns:
        bool: True if watermark was successfully removed
    """
    remover = WatermarkRemover()
    return await remover.remove_watermark(
        input_file,
        output_file,
        progress_callback
    )
