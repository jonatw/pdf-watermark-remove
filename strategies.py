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
import asyncio
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
        input_file: Path, 
        output_file: Path,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> bool:
        """
        Remove watermark from PDF file.
        
        Args:
            input_file: Path to input PDF file
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
        logger.debug(f"Initialized XRefImageRemovalStrategy with patterns: {self.patterns}")
    
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
        logger.debug(f"XRef strategy can handle: {can_handle} (producer: {producer})")
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
            logger.debug(f"Found {len(image_list)} images on page")
            
            for image_info in image_list:
                for pattern in self.patterns:
                    if (image_info["width"] == pattern["width"] and 
                        image_info["height"] == pattern["height"]):
                        logger.info(
                            f"Found watermark image with dimensions "
                            f"{pattern['width']}x{pattern['height']}, "
                            f"XRef: {image_info['xref']}"
                        )
                        return image_info["xref"]
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding watermark XRef: {str(e)}")
            raise StrategyError(f"Failed to find watermark XRef: {str(e)}")
    
    async def remove(
        self, 
        input_file: Path, 
        output_file: Path,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> bool:
        """
        Remove watermark using XRef image removal strategy.
        
        Args:
            input_file: Path to input PDF file
            output_file: Path to output PDF file
            progress_callback: Optional callback for progress updates
            
        Returns:
            bool: True if watermark was removed, False otherwise
            
        Raises:
            PDFProcessingError: If there's an error processing the PDF
        """
        try:
            # Report progress
            if progress_callback:
                progress_callback("Opening PDF", 0.1)
                
            doc = fitz.open(str(input_file))
            logger.info(f"Opened PDF with {len(doc)} pages")
            
            # Check first page for watermark
            if len(doc) == 0:
                raise InvalidPDFError("PDF has no pages")
            
            # Report progress
            if progress_callback:
                progress_callback("Finding watermark", 0.3)
                
            target_xref = self._find_watermark_xref(doc[0])
            
            if not target_xref:
                logger.warning("No watermark XRef found on first page")
                return False
            
            # Report progress
            if progress_callback:
                progress_callback("Removing watermark", 0.5)
                
            # Remove watermark image
            doc[0].delete_image(target_xref)
            logger.info(f"Deleted watermark image with XRef: {target_xref}")
            
            # Report progress
            if progress_callback:
                progress_callback("Saving document", 0.8)
                
            # Save the modified document
            doc.ez_save(str(output_file))
            logger.info(f"Saved processed PDF to: {output_file}")
            
            # Report progress
            if progress_callback:
                progress_callback("Complete", 1.0)
                
            doc.close()
            return True
            
        except Exception as e:
            logger.error(f"Error in XRef removal strategy: {str(e)}")
            raise PDFProcessingError(f"XRef removal failed: {str(e)}")


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
            f"Initialized CommonStringRemovalStrategy with min_length: "
            f"{self.min_length}, window: {self.window}"
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
    
    def _find_most_frequent_text_tj_substring(
        self, 
        doc: fitz.Document,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Tuple[bytes, int]:
        """
        Find the most frequently occurring TJ substring in the document.
        
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
            # Report progress
            if progress_callback and total_pages > 0:
                progress = page_idx / total_pages
                progress_callback(f"Analyzing page {page_idx+1}/{total_pages}", progress)
                
            for xref in page.get_contents():
                content = doc.xref_stream(xref)
                i = 0
                while i < len(content):
                    # Check for '(' pattern
                    if content[i:i+1] == b'(':
                        end = content.find(b') Tj', i)
                        if end != -1 and end - i < self.window:
                            substring = content[i:end+4]
                            if len(substring) >= self.min_length:
                                counter[substring] += 1
                            i = end + 4
                            continue
                    
                    # Check for '<' pattern
                    if content[i:i+1] == b'<':
                        end = content.find(b'> Tj', i)
                        if end != -1 and end - i < self.window:
                            substring = content[i:end+4]
                            if len(substring) >= self.min_length:
                                counter[substring] += 1
                            i = end + 4
                            continue
                    
                    # Check for '[' pattern
                    if content[i:i+1] == b'[':
                        end = content.find(b'] TJ', i)
                        if end != -1 and end - i < self.window:
                            substring = content[i:end+5]
                            if len(substring) >= self.min_length:
                                counter[substring] += 1
                            i = end + 5
                            continue
                    
                    i += 1
        
        if not counter:
            logger.warning("No watermark pattern found in document")
            return None, 0
        
        # Log top 5 candidates
        logger.info("Top 5 candidates (min length applied):")
        for s, c in counter.most_common(5):
            try:
                logger.info(f"  {s.decode('utf-8', errors='replace')} x {c}")
            except:
                logger.info(f"  {s[:60]}... x {c}")
        
        # Find most frequent pattern
        most_frequent, frequency = counter.most_common(1)[0]
        
        return most_frequent, frequency
    
    async def _remove_watermark_from_page(
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
            # Report progress
            if progress_callback:
                progress = page_number / total_pages
                progress_callback(f"Processing page {page_number+1}/{total_pages}", progress)
                
            page = doc[page_number]
            replaced = 0
            
            for xref in page.get_contents():
                raw = doc.xref_stream(xref)
                raw_str = raw.decode("latin1")
                
                # Find and remove blocks containing the target string
                blocks = re.findall(r"q\s+.*?Q", raw_str, flags=re.DOTALL)
                for block in blocks:
                    if target_str in block:
                        raw_str = raw_str.replace(block, "")
                        replaced += 1
                
                if replaced:
                    # Update the page content
                    doc.update_stream(xref, raw_str.encode("latin1"))
            
            return replaced
            
        except Exception as e:
            logger.error(f"Error removing pattern from page {page_number}: {str(e)}")
            raise StrategyError(f"Failed to remove pattern from page {page_number}: {str(e)}")
    
    async def remove(
        self, 
        input_file: Path, 
        output_file: Path,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> bool:
        """
        Remove watermark using common string removal strategy.
        
        Args:
            input_file: Path to input PDF file
            output_file: Path to output PDF file
            progress_callback: Optional callback for progress updates
            
        Returns:
            bool: True if watermark was removed, False otherwise
            
        Raises:
            PDFProcessingError: If there's an error processing the PDF
        """
        try:
            # Report progress
            if progress_callback:
                progress_callback("Opening PDF", 0.05)
                
            doc = fitz.open(str(input_file))
            logger.info(f"Opened PDF with {len(doc)} pages")
            
            if len(doc) == 0:
                raise InvalidPDFError("PDF has no pages")
            
            # Report progress
            if progress_callback:
                progress_callback("Analyzing document", 0.1)
                
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
            except:
                target_str = most_common.hex()
            
            logger.info(f"Detected watermark (freq={freq}):")
            logger.info(target_str)
            
            # Report progress
            if progress_callback:
                progress_callback("Removing watermark", 0.4)
                
            # Prepare progress tracking for page processing
            total_pages = len(doc)
            
            # Remove pattern from all pages concurrently
            tasks = [
                self._remove_watermark_from_page(
                    doc, 
                    page.number, 
                    target_str,
                    lambda s, p: progress_callback(s, 0.4 + p * 0.5) if progress_callback else None,
                    total_pages
                ) 
                for page in doc
            ]
            
            await asyncio.gather(*tasks)
            
            # Report progress
            if progress_callback:
                progress_callback("Saving document", 0.9)
                
            # Save the modified document
            doc.save(str(output_file), garbage=4, deflate=True, clean=True)
            logger.info(f"Saved processed PDF to: {output_file}")
            
            # Report progress
            if progress_callback:
                progress_callback("Complete", 1.0)
                
            doc.close()
            return True
            
        except Exception as e:
            logger.error(f"Error in common string removal strategy: {str(e)}")
            raise PDFProcessingError(f"Common string removal failed: {str(e)}")
