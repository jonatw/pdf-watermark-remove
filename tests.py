"""
Unit tests for PDF Watermark Remover.

This module contains unit tests for the PDF Watermark Remover package.
It tests various components of the package, including the configuration,
watermark removal strategies, and error handling.

To run the tests:
    python -m unittest tests.py

Author: PDF Watermark Remover Team
Version: 2.0.0
"""

import os
import sys
import tempfile
import unittest
import asyncio
from pathlib import Path
import fitz

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import package modules
from config import Config, WatermarkPattern
from exceptions import (
    PDFWatermarkRemoverError,
    PDFProcessingError,
    InvalidPDFError,
    WatermarkNotFoundError,
    StrategyError
)
from strategies import (
    WatermarkRemovalStrategy,
    XRefImageRemovalStrategy,
    OCGWatermarkRemovalStrategy,
    CommonStringRemovalStrategy
)
from remove_watermark import WatermarkRemover, remove_watermark, ProgressCallback


class TestConfig(unittest.TestCase):
    """Test cases for configuration module."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = Config()
        self.assertEqual(config.VERSION, "2.0.0")
        self.assertEqual(config.LOG_LEVEL, "INFO")
        self.assertEqual(config.MAX_CONCURRENT_PAGES, 8)
        self.assertEqual(config.MIN_PATTERN_LENGTH, 30)
        self.assertEqual(config.PATTERN_SEARCH_WINDOW, 300)
        self.assertEqual(config.XREF_PRODUCER_PATTERNS, ["Version"])
    
    def test_environment_variables(self):
        """Test configuration from environment variables."""
        # Reset singleton so env vars are picked up
        Config.reset()

        # Set environment variables
        os.environ["PDF_WATERMARK_LOG_LEVEL"] = "DEBUG"
        os.environ["PDF_WATERMARK_MAX_CONCURRENT_PAGES"] = "4"

        try:
            config = Config()
            self.assertEqual(config.LOG_LEVEL, "DEBUG")
            self.assertEqual(config.MAX_CONCURRENT_PAGES, 4)
        finally:
            del os.environ["PDF_WATERMARK_LOG_LEVEL"]
            del os.environ["PDF_WATERMARK_MAX_CONCURRENT_PAGES"]
            Config.reset()

    def test_singleton_pattern(self):
        """Test that Config follows the singleton pattern."""
        config1 = Config()
        config2 = Config()
        self.assertIs(config1, config2)


class TestExceptions(unittest.TestCase):
    """Test cases for exception classes."""
    
    def test_exception_hierarchy(self):
        """Test exception class hierarchy."""
        self.assertTrue(issubclass(PDFProcessingError, PDFWatermarkRemoverError))
        self.assertTrue(issubclass(InvalidPDFError, PDFProcessingError))
        self.assertTrue(issubclass(WatermarkNotFoundError, PDFProcessingError))
        self.assertTrue(issubclass(StrategyError, PDFProcessingError))
    
    def test_exception_messages(self):
        """Test exception messages."""
        self.assertEqual(str(PDFWatermarkRemoverError()), "An error occurred in PDF Watermark Remover")
        self.assertEqual(str(PDFProcessingError()), "Error processing PDF file")
        self.assertEqual(str(InvalidPDFError()), "Invalid PDF file")
        self.assertEqual(str(WatermarkNotFoundError()), "No watermark pattern found in document")
        self.assertEqual(str(StrategyError()), "Error in watermark removal strategy")
        
        # Custom message
        self.assertEqual(str(PDFWatermarkRemoverError("Custom message")), "Custom message")


class TestProgressCallback(unittest.TestCase):
    """Test cases for progress callback."""
    
    def test_progress_callback(self):
        """Test progress callback functionality."""
        # Create mock callback function
        status_messages = []
        progress_values = []
        
        def callback(status, progress):
            status_messages.append(status)
            progress_values.append(progress)
        
        # Create progress callback
        progress = ProgressCallback(callback, 10)
        
        # Test initial state
        self.assertEqual(progress.total_steps, 10)
        self.assertEqual(progress.current_step, 0)
        self.assertEqual(progress.current_status, "")
        
        # Test update with status
        progress.update("Starting", 0)
        self.assertEqual(status_messages[-1], "Starting")
        self.assertEqual(progress_values[-1], 0.0)
        
        # Test update with increment
        progress.update("Processing", increment=1)
        self.assertEqual(status_messages[-1], "Processing")
        self.assertEqual(progress_values[-1], 0.1)
        
        # Test update with absolute step
        progress.update("Halfway", 5)
        self.assertEqual(status_messages[-1], "Halfway")
        self.assertEqual(progress_values[-1], 0.5)
        
        # Test update without status
        progress.update(increment=1)
        self.assertEqual(status_messages[-1], "Halfway")  # Status doesn't change
        self.assertEqual(progress_values[-1], 0.6)
        
        # Test update beyond total
        progress.update("Complete", 10)
        self.assertEqual(status_messages[-1], "Complete")
        self.assertEqual(progress_values[-1], 1.0)


class TestWatermarkRemover(unittest.TestCase):
    """Test cases for WatermarkRemover class."""
    
    def test_invalid_file(self):
        """Test handling of invalid files."""
        remover = WatermarkRemover()
        
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            tmp_path = Path(tmp.name)
            output_path = tmp_path.with_suffix(".out.pdf")
            
            # Write invalid PDF content
            tmp.write(b"This is not a PDF file")
            tmp.flush()
            
            # Should raise InvalidPDFError
            with self.assertRaises(Exception):
                asyncio.run(
                    remover.remove_watermark(str(tmp_path), str(output_path))
                )
    
    def test_nonexistent_file(self):
        """Test handling of nonexistent files."""
        remover = WatermarkRemover()
        with self.assertRaises(InvalidPDFError):
            asyncio.run(
                remover.remove_watermark(
                    "nonexistent.pdf", 
                    "output.pdf"
                )
            )


class TestStrategies(unittest.TestCase):
    """Test cases for watermark removal strategies."""
    
    def test_xref_strategy_patterns(self):
        """Test XRef strategy patterns."""
        # Custom patterns
        patterns = [
            {"width": 100, "height": 200},
            {"width": 300, "height": 400}
        ]
        
        strategy = XRefImageRemovalStrategy(patterns)
        
        # Check patterns
        self.assertEqual(len(strategy.patterns), 2)
        self.assertEqual(strategy.patterns[0]["width"], 100)
        self.assertEqual(strategy.patterns[0]["height"], 200)
        self.assertEqual(strategy.patterns[1]["width"], 300)
        self.assertEqual(strategy.patterns[1]["height"], 400)
    
    def test_common_string_strategy_params(self):
        """Test Common String strategy parameters."""
        # Custom parameters
        min_length = 50
        window = 400
        
        strategy = CommonStringRemovalStrategy(min_length, window)
        
        # Check parameters
        self.assertEqual(strategy.min_length, 50)
        self.assertEqual(strategy.window, 400)


class TestOCGWatermarkStrategy(unittest.TestCase):
    """Test cases for OCG Watermark removal strategy."""

    def test_can_handle_with_ocg_watermark(self):
        """Test that strategy detects OCG Watermark layer."""
        rjbb = "data/RJBB.pdf"
        if not os.path.exists(rjbb):
            self.skipTest("data/RJBB.pdf not available")
        strategy = OCGWatermarkRemovalStrategy()
        doc = fitz.open(rjbb)
        self.assertTrue(strategy.can_handle(doc))
        doc.close()

    def test_can_handle_without_ocg_watermark(self):
        """Test that strategy rejects PDFs without OCG Watermark layer."""
        # Create a plain PDF with no OCG
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            doc = fitz.Document()
            page = doc.new_page()
            page.insert_text((72, 72), "Hello", fontsize=12)
            doc.save(tmp.name)
            doc.close()

            doc = fitz.open(tmp.name)
            strategy = OCGWatermarkRemovalStrategy()
            self.assertFalse(strategy.can_handle(doc))
            doc.close()
            os.unlink(tmp.name)

    def test_ocg_removal_on_rjbb(self):
        """Test OCG watermark removal produces clean output."""
        rjbb = "data/RJBB.pdf"
        if not os.path.exists(rjbb):
            self.skipTest("data/RJBB.pdf not available")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            output = tmp.name

        try:
            remover = WatermarkRemover()
            result = asyncio.run(remover.remove_watermark(rjbb, output))
            self.assertTrue(result)

            # Verify output has no remaining watermark structures
            doc = fitz.open(output)
            for i in range(1, doc.xref_length()):
                obj = doc.xref_object(i)
                self.assertNotIn("/Private /Watermark", obj,
                    f"Watermark Form XObject remnant at xref {i}")
            doc.close()
        finally:
            if os.path.exists(output):
                os.unlink(output)


class TestRasterizedDetection(unittest.TestCase):
    """Test cases for rasterized-only PDF detection."""

    def _create_rasterized_pdf(self, path):
        """Create a minimal PDF with only a full-page image and no text."""
        doc = fitz.Document()
        page = doc.new_page(width=612, height=792)
        # Insert a dummy image (1x1 white pixel PNG)
        import struct, zlib
        raw = b'\x00\xff\xff\xff'
        compressed = zlib.compress(raw)
        ihdr = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
        def chunk(ctype, data):
            c = ctype + data
            return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
        png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')
        rect = fitz.Rect(0, 0, 612, 792)
        page.insert_image(rect, stream=png)
        doc.save(str(path))
        doc.close()

    def _create_text_pdf(self, path):
        """Create a minimal PDF with text content."""
        doc = fitz.Document()
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 72), "Hello World", fontsize=12)
        doc.save(str(path))
        doc.close()

    def test_rasterized_pdf_detected(self):
        """Test that a rasterized-only PDF is detected."""
        remover = WatermarkRemover()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            self._create_rasterized_pdf(tmp.name)
            doc = fitz.open(tmp.name)
            self.assertTrue(remover._is_rasterized_only(doc))
            doc.close()
            os.unlink(tmp.name)

    def test_text_pdf_not_detected(self):
        """Test that a PDF with text is not flagged as rasterized."""
        remover = WatermarkRemover()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            self._create_text_pdf(tmp.name)
            doc = fitz.open(tmp.name)
            self.assertFalse(remover._is_rasterized_only(doc))
            doc.close()
            os.unlink(tmp.name)

    def test_rasterized_pdf_returns_false(self):
        """Test that remove_watermark returns False for rasterized PDFs."""
        remover = WatermarkRemover()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            self._create_rasterized_pdf(tmp.name)
            output = tmp.name + ".out.pdf"
            result = asyncio.run(remover.remove_watermark(tmp.name, output))
            self.assertFalse(result)
            os.unlink(tmp.name)
            if os.path.exists(output):
                os.unlink(output)

class TestMetadataSanitization(unittest.TestCase):
    """Test cases for metadata sanitization."""

    def test_generalize_date(self):
        """Test date truncation to year-month."""
        self.assertEqual(
            WatermarkRemover._generalize_date("D:20260330234506+08'00'"),
            "D:20260301000000+00'00'"
        )
        self.assertEqual(
            WatermarkRemover._generalize_date("D:20260326101009+08'00'"),
            "D:20260301000000+00'00'"
        )
        self.assertEqual(WatermarkRemover._generalize_date(""), "")
        self.assertEqual(WatermarkRemover._generalize_date("invalid"), "")

    def test_generalize_producer(self):
        """Test producer string generalization."""
        self.assertEqual(
            WatermarkRemover._generalize_producer(
                "PDFsharp 1.50.4000-netstandard (https://example.com) (Original: Word)"
            ),
            "PDFsharp"
        )
        self.assertEqual(
            WatermarkRemover._generalize_producer(
                "iOS Version 26.3.1 (Build 23D771330a) Quartz PDFContext"
            ),
            "Quartz PDFContext"
        )
        self.assertEqual(
            WatermarkRemover._generalize_producer("Skia/PDF m146"),
            "Skia/PDF"
        )
        self.assertEqual(
            WatermarkRemover._generalize_producer(""),
            ""
        )

    def test_sanitize_on_real_pdf(self):
        """Test full sanitization on RJBB.pdf output."""
        rjbb = "data/RJBB.pdf"
        if not os.path.exists(rjbb):
            self.skipTest("data/RJBB.pdf not available")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            output = tmp.name

        try:
            remover = WatermarkRemover()
            result = asyncio.run(remover.remove_watermark(rjbb, output))
            self.assertTrue(result)

            doc = fitz.open(output)
            meta = doc.metadata

            # Dates should be truncated to year-month
            self.assertIn("01000000", meta.get("creationDate", ""))
            self.assertIn("+00'00'", meta.get("creationDate", ""))

            # Author and creator should be empty
            self.assertEqual(meta.get("author", ""), "")
            self.assertEqual(meta.get("creator", ""), "")

            # Producer should be stripped of versions
            producer = meta.get("producer", "")
            self.assertNotIn("1.50", producer)
            self.assertNotIn("github", producer.lower())

            # XMP should be empty
            xmp = doc.get_xml_metadata()
            self.assertTrue(xmp == "" or xmp is None or len(xmp.strip()) == 0)

            doc.close()
        finally:
            if os.path.exists(output):
                os.unlink(output)

    def test_pdf_id_stripped(self):
        """Test that PDF /ID arrays are removed from output."""
        rjbb = "data/RJBB.pdf"
        if not os.path.exists(rjbb):
            self.skipTest("data/RJBB.pdf not available")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            output = tmp.name

        try:
            import re
            remover = WatermarkRemover()
            asyncio.run(remover.remove_watermark(rjbb, output))

            with open(output, 'rb') as f:
                data = f.read()
            matches = re.findall(rb'/ID\s*\[<[0-9A-Fa-f]+><[0-9A-Fa-f]+>\]', data)
            self.assertEqual(len(matches), 0, "PDF /ID array should be stripped")
        finally:
            if os.path.exists(output):
                os.unlink(output)


if __name__ == "__main__":
    unittest.main()
