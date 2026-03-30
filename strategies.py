"""
Watermark removal strategies for PDF Watermark Remover.

This module implements various strategies for removing watermarks from PDF files.
Each strategy is specialized for a specific type of watermark:
1. XRefImageRemovalStrategy - for image-based watermarks with known dimensions
2. CommonStringRemovalStrategy - for text-based watermarks with repeating patterns

Author: PDF Watermark Remover Team
Version: 2.0.0
"""

import re
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict, Any, Counter as CounterType, Callable
from pathlib import Path
from collections import Counter
import fitz  # PyMuPDF

from config import Config
from exceptions import (
    PDFProcessingError,
    WatermarkNotFoundError,
    InvalidPDFError,
    StrategyError
)
from logging_utils import get_logger


# Configure logging
logger = get_logger(__name__)


class WatermarkRemovalStrategy(ABC):
    """Abstract base class for watermark removal strategies."""
    
    @abstractmethod
    async def remove(
        self,
        doc: fitz.Document,
        output_file: Path,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> bool:
        """
        Remove watermark from an opened PDF document.

        Args:
            doc: Already-opened PyMuPDF document (caller manages open/close)
            output_file: Path to output PDF file
            progress_callback: Optional callback for progress updates

        Returns:
            bool: True if watermark was successfully removed, False otherwise

        Raises:
            PDFProcessingError: If there's an error processing the PDF
        """
        pass
    
    @abstractmethod
    def can_handle(self, doc: fitz.Document) -> bool:
        """
        Check if this strategy can handle the given PDF document.
        
        Args:
            doc: PyMuPDF document object
            
        Returns:
            bool: True if this strategy can handle the document
        """
        pass


class XRefImageRemovalStrategy(WatermarkRemovalStrategy):
    """
    Strategy for removing image-based watermarks using XRef.
    
    This strategy identifies watermark images by their dimensions and removes
    them directly using their cross-reference (XRef) IDs. It's fast and 
    effective for PDFs with image watermarks of known sizes.
    """
    
    def __init__(self, patterns: List[Dict[str, int]] = None, config_file: Optional[str] = None):
        """
        Initialize the XRef removal strategy.
        
        Args:
            patterns: List of watermark dimension patterns to match
            config_file: Path to configuration file (optional)
        """
        # Load configuration
        self.config = Config(config_file)
        
        self.patterns = patterns or [
            {"width": pattern.width, "height": pattern.height}
            for pattern in self.config.WATERMARK_PATTERNS
        ]
        logger.debug("Initialized XRefImageRemovalStrategy with %d patterns", len(self.patterns))
    
    def can_handle(self, doc: fitz.Document) -> bool:
        """
        Check if document metadata indicates XRef strategy should be used.
        
        Args:
            doc: PyMuPDF document object
            
        Returns:
            bool: True if producer metadata contains trigger patterns
        """
        producer = doc.metadata.get("producer", "")
        can_handle = any(
            pattern in producer 
            for pattern in self.config.XREF_PRODUCER_PATTERNS
        )
        logger.debug("XRef strategy can handle: %s (producer: %s)", can_handle, producer)
        return can_handle
    
    def _find_watermark_xref(self, page: fitz.Page) -> Optional[int]:
        """
        Find watermark image XRef on the given page.
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            Optional[int]: XRef ID of watermark image, or None if not found
        """
        try:
            image_list = page.get_image_info(xrefs=True)
            logger.debug("Found %d images on page", len(image_list))
            
            for image_info in image_list:
                for pattern in self.patterns:
                    if (image_info["width"] == pattern["width"] and 
                        image_info["height"] == pattern["height"]):
                        logger.info(
                            "Found watermark image %dx%d, XRef: %d",
                            pattern['width'], pattern['height'], image_info['xref']
                        )
                        return image_info["xref"]
            
            return None
            
        except Exception as e:
            logger.error("Error finding watermark XRef: %s", e)
            raise StrategyError(f"Failed to find watermark XRef: {str(e)}")
    
    async def remove(
        self,
        doc: fitz.Document,
        output_file: Path,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> bool:
        """
        Remove watermark using XRef image removal strategy.

        Args:
            doc: Already-opened PyMuPDF document (caller manages open/close)
            output_file: Path to output PDF file
            progress_callback: Optional callback for progress updates

        Returns:
            bool: True if watermark was removed, False otherwise

        Raises:
            PDFProcessingError: If there's an error processing the PDF
        """
        try:
            if progress_callback:
                progress_callback("Finding watermark", 0.3)

            if len(doc) == 0:
                raise InvalidPDFError("PDF has no pages")

            target_xref = self._find_watermark_xref(doc[0])

            if not target_xref:
                logger.warning("No watermark XRef found on first page")
                return False

            if progress_callback:
                progress_callback("Removing watermark", 0.5)

            doc[0].delete_image(target_xref)
            logger.info("Deleted watermark image with XRef: %d", target_xref)

            if progress_callback:
                progress_callback("Saving document", 0.8)

            doc.save(str(output_file))
            logger.info("Saved processed PDF to: %s", output_file)

            if progress_callback:
                progress_callback("Complete", 1.0)

            return True

        except Exception as e:
            logger.error("Error in XRef removal strategy: %s", e)
            raise PDFProcessingError(f"XRef removal failed: {str(e)}")

class OCGWatermarkRemovalStrategy(WatermarkRemovalStrategy):
    """
    Strategy for removing watermarks embedded as OCG (Optional Content Group) layers.

    This strategy detects PDFs where the watermark is a named OCG layer
    (e.g. /Name (Watermark)) with Form XObjects tagged /Private /Watermark.
    It removes the watermark content streams, Form XObjects, and OCG structure.
    Typical for website-downloaded PDFs generated by PDFsharp.
    """

    def __init__(self):
        self._cached_ocg_info = None

    def can_handle(self, doc: fitz.Document) -> bool:
        """
        Check if document has an OCG layer named 'Watermark'.
        Also caches the full xref scan result for use in remove().

        Args:
            doc: PyMuPDF document object

        Returns:
            bool: True if an OCG Watermark layer is found
        """
        # Single scan: detect and cache all OCG-related xrefs
        result = {"ocg": None, "ocmd": None, "form_xobjects": []}
        for i in range(1, doc.xref_length()):
            obj = doc.xref_object(i)
            if "/Type /OCG" in obj and "Watermark" in obj:
                result["ocg"] = i
            if "/Type /OCMD" in obj:
                result["ocmd"] = i
            if "/Private /Watermark" in obj:
                result["form_xobjects"].append(i)

        self._cached_ocg_info = result

        if result["ocg"] is not None:
            logger.debug("Found OCG Watermark layer at xref %d", result["ocg"])
            return True
        return False

    def _is_watermark_content_stream(self, doc: fitz.Document, xref: int) -> bool:
        """
        Determine if a content stream is watermark-only.

        Watermark content streams contain rotation matrices and text drawing
        but no BDC/EMC marked content (which indicates actual page content).
        """
        try:
            stream = doc.xref_stream(xref).decode("latin1")
            has_rotation = "0.819152" in stream or "0.5735764" in stream
            has_marked_content = "BDC" in stream
            return has_rotation and not has_marked_content
        except Exception:
            return False

    async def remove(
        self,
        doc: fitz.Document,
        output_file: Path,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> bool:
        """
        Remove watermark by stripping the OCG Watermark layer and all associated objects.
        """
        try:
            if len(doc) == 0:
                raise InvalidPDFError("PDF has no pages")

            if progress_callback:
                progress_callback("Finding OCG Watermark layer", 0.1)

            # Use cached result from can_handle() if available
            ocg_info = self._cached_ocg_info
            if ocg_info is None:
                # Fallback: scan now (shouldn't happen in normal flow)
                self.can_handle(doc)
                ocg_info = self._cached_ocg_info

            if ocg_info["ocg"] is None:
                logger.warning("No OCG Watermark layer found")
                return False

            logger.info(
                "OCG structure: OCG=%s, OCMD=%s, Form XObjects=%s",
                ocg_info['ocg'], ocg_info['ocmd'], ocg_info['form_xobjects']
            )

            if progress_callback:
                progress_callback("Removing watermark content streams", 0.3)

            # Step 1: Remove watermark content streams from each page
            total_pages = len(doc)
            removed_streams = 0
            for pg_num in range(total_pages):
                page = doc[pg_num]
                content_xrefs = list(page.get_contents())

                for xref in content_xrefs:
                    if self._is_watermark_content_stream(doc, xref):
                        doc.update_stream(xref, b"")
                        removed_streams += 1
                        logger.debug("Cleared watermark stream xref %d on page %d", xref, pg_num)

                if progress_callback:
                    progress_callback(
                        "Processing page %d/%d" % (pg_num + 1, total_pages),
                        0.3 + 0.3 * (pg_num + 1) / total_pages
                    )

            logger.info("Cleared %d watermark content streams", removed_streams)

            if progress_callback:
                progress_callback("Removing watermark Form XObjects", 0.65)

            # Step 2: Clear Form XObjects tagged as watermark
            for xref in ocg_info["form_xobjects"]:
                try:
                    doc.update_stream(xref, b"")
                    doc.xref_set_key(xref, "PieceInfo", "null")
                    doc.xref_set_key(xref, "OC", "null")
                    doc.xref_set_key(xref, "LastModified", "null")
                    logger.debug("Cleared watermark Form XObject xref %d", xref)
                except Exception as e:
                    logger.warning("Could not clear Form XObject xref %d: %s", xref, e)

            if progress_callback:
                progress_callback("Cleaning OCG structure", 0.75)

            # Step 3: Remove OCG structure
            try:
                for i in range(1, doc.xref_length()):
                    obj = doc.xref_object(i)
                    if "/Type /Catalog" in obj and "/OCProperties" in obj:
                        doc.xref_set_key(i, "OCProperties", "null")
                        logger.info("Removed /OCProperties from catalog xref %d", i)
                        break

                if ocg_info["ocg"]:
                    doc.xref_set_key(ocg_info["ocg"], "Type", "null")
                    doc.xref_set_key(ocg_info["ocg"], "Name", "null")
                    doc.xref_set_key(ocg_info["ocg"], "Usage", "null")
                    logger.debug("Cleared OCG group xref %s", ocg_info['ocg'])

                if ocg_info["ocmd"]:
                    doc.xref_set_key(ocg_info["ocmd"], "Type", "null")
                    doc.xref_set_key(ocg_info["ocmd"], "OCGs", "null")
                    logger.debug("Cleared OCMD xref %s", ocg_info['ocmd'])
            except Exception as e:
                logger.warning("Could not clean OCG structure: %s", e)

            if progress_callback:
                progress_callback("Saving document", 0.85)

            doc.save(str(output_file))
            logger.info("Saved processed PDF to: %s", output_file)

            if progress_callback:
                progress_callback("Complete", 1.0)

            return True

        except Exception as e:
            logger.error("Error in OCG watermark removal: %s", e)
            raise PDFProcessingError(f"OCG watermark removal failed: {str(e)}")

class CommonStringRemovalStrategy(WatermarkRemovalStrategy):
    """
    Strategy for removing text-based watermarks using pattern matching.
    
    This strategy identifies frequently occurring text patterns that match
    watermark characteristics and removes them from all pages. It's effective
    for text-based watermarks that appear consistently across pages.
    """
    
    def __init__(self, min_length: int = None, window: int = None, config_file: Optional[str] = None):
        """
        Initialize the common string removal strategy.
        
        Args:
            min_length: Minimum length for a pattern to be considered a watermark
            window: Maximum window size to search for patterns
            config_file: Path to configuration file (optional)
        """
        # Load configuration
        self.config = Config(config_file)
        
        self.min_length = min_length or self.config.MIN_PATTERN_LENGTH
        self.window = window or self.config.PATTERN_SEARCH_WINDOW
        logger.debug(
            "Initialized CommonStringRemovalStrategy with min_length: %d, window: %d",
            self.min_length, self.window
        )
    
    def can_handle(self, doc: fitz.Document) -> bool:
        """
        This strategy can handle any PDF document.
        
        Args:
            doc: PyMuPDF document object
            
        Returns:
            bool: Always returns True as fallback strategy
        """
        return True
    
    # Compiled regex for TJ pattern extraction — delegates to C engine
    _TJ_PATTERN = re.compile(
        rb'\(([^)]*)\) Tj|<([^>]*)> Tj|\[([^\]]*)\] TJ'
    )

    def _find_most_frequent_text_tj_substring(
        self,
        doc: fitz.Document,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Tuple[bytes, int]:
        """
        Find the most frequently occurring TJ substring in the document.

        Uses a compiled regex to scan content streams in a single pass per stream,
        delegating byte-level matching to the C regex engine.

        Args:
            doc: PyMuPDF document object
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple[bytes, int]: Most frequent substring and its count

        Raises:
            WatermarkNotFoundError: If no pattern is found
        """
        counter: CounterType[bytes] = Counter()
        total_pages = len(doc)

        for page_idx, page in enumerate(doc):
            if progress_callback and total_pages > 0:
                progress = page_idx / total_pages
                progress_callback("Analyzing page %d/%d" % (page_idx + 1, total_pages), progress)

            for xref in page.get_contents():
                content = doc.xref_stream(xref)
                for match in self._TJ_PATTERN.finditer(content):
                    substring = match.group()
                    if self.min_length <= len(substring) <= self.window:
                        counter[substring] += 1

        if not counter:
            logger.warning("No watermark pattern found in document")
            return None, 0

        # Log top 5 candidates
        logger.info("Top 5 candidates (min length applied):")
        for s, c in counter.most_common(5):
            try:
                logger.info("  %s x %d", s.decode('utf-8', errors='replace'), c)
            except Exception:
                logger.info("  %s... x %d", s[:60], c)

        # Find most frequent pattern
        most_frequent, frequency = counter.most_common(1)[0]

        return most_frequent, frequency

    
    def _remove_watermark_from_page(
        self,
        doc: fitz.Document,
        page_number: int,
        target_str: str,
        progress_callback: Optional[Callable[[str, float], None]] = None,
        total_pages: int = 1
    ) -> int:
        """
        Remove all occurrences of pattern from a single page.

        Args:
            doc: PyMuPDF document object
            page_number: Page number to process
            target_str: String pattern to remove
            progress_callback: Optional callback for progress updates
            total_pages: Total number of pages (for progress calculation)

        Returns:
            int: Number of replacements made
        """
        try:
            if progress_callback:
                progress = page_number / total_pages
                progress_callback("Processing page %d/%d" % (page_number + 1, total_pages), progress)

            page = doc[page_number]
            replaced = 0

            for xref in page.get_contents():
                raw = doc.xref_stream(xref)
                raw_str = raw.decode("latin1")

                # Single-pass removal of q...Q blocks containing the target string
                def replacer(m):
                    nonlocal replaced
                    if target_str in m.group():
                        replaced += 1
                        return ''
                    return m.group()

                new_str = re.sub(r'q\s+.*?Q', replacer, raw_str, flags=re.DOTALL)

                if replaced:
                    doc.update_stream(xref, new_str.encode("latin1"))

            return replaced

        except Exception as e:
            logger.error("Error removing pattern from page %d: %s", page_number, e)
            raise StrategyError(f"Failed to remove pattern from page {page_number}: {str(e)}")
    async def remove(
        self,
        doc: fitz.Document,
        output_file: Path,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> bool:
        """
        Remove watermark using common string removal strategy.

        Args:
            doc: Already-opened PyMuPDF document (caller manages open/close)
            output_file: Path to output PDF file
            progress_callback: Optional callback for progress updates

        Returns:
            bool: True if watermark was removed, False otherwise

        Raises:
            PDFProcessingError: If there's an error processing the PDF
        """
        try:
            if progress_callback:
                progress_callback("Analyzing document", 0.1)

            if len(doc) == 0:
                raise InvalidPDFError("PDF has no pages")

            # Find most frequent pattern
            most_common, freq = self._find_most_frequent_text_tj_substring(
                doc,
                lambda s, p: progress_callback(s, 0.1 + p * 0.3) if progress_callback else None
            )

            if not most_common or freq < 1:
                logger.warning("No watermark pattern detected")
                return False

            # Convert pattern to string
            try:
                target_str = most_common.decode('latin1').strip()
            except Exception:
                target_str = most_common.hex()

            logger.info("Detected watermark (freq=%d):", freq)
            logger.info(target_str)

            if progress_callback:
                progress_callback("Removing watermark", 0.4)

            total_pages = len(doc)

            # Remove pattern from all pages sequentially
            # (PyMuPDF doc is not thread-safe; async gather had no real parallelism)
            for page in doc:
                self._remove_watermark_from_page(
                    doc,
                    page.number,
                    target_str,
                    lambda s, p: progress_callback(s, 0.4 + p * 0.5) if progress_callback else None,
                    total_pages
                )

            if progress_callback:
                progress_callback("Saving document", 0.9)

            doc.save(str(output_file))
            logger.info("Saved processed PDF to: %s", output_file)

            if progress_callback:
                progress_callback("Complete", 1.0)

            return True

        except Exception as e:
            logger.error("Error in common string removal strategy: %s", e)
            raise PDFProcessingError(f"Common string removal failed: {str(e)}")
