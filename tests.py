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
        # Set environment variables
        os.environ["PDF_WATERMARK_LOG_LEVEL"] = "DEBUG"
        os.environ["PDF_WATERMARK_MAX_CONCURRENT_PAGES"] = "4"
        
        # Create new config instance
        config = Config()
        
        # Check values
        self.assertEqual(config.LOG_LEVEL, "DEBUG")
        self.assertEqual(config.MAX_CONCURRENT_PAGES, 4)
        
        # Clean up
        del os.environ["PDF_WATERMARK_LOG_LEVEL"]
        del os.environ["PDF_WATERMARK_MAX_CONCURRENT_PAGES"]
    
    def test_yaml_config(self):
        """Test configuration from YAML file."""
        # Skip test if PyYAML is not available
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML not available")
            
        # Create temporary YAML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp:
            temp.write("""
VERSION: "2.1.0"
LOG_LEVEL: "DEBUG"
MAX_CONCURRENT_PAGES: 16
WATERMARK_PATTERNS:
  - width: 1000
    height: 500
            """)
            temp_path = temp.name
        
        try:
            # Create config from file
            config = Config(temp_path)
            
            # Check values
            self.assertEqual(config.VERSION, "2.1.0")
            self.assertEqual(config.LOG_LEVEL, "DEBUG")
            self.assertEqual(config.MAX_CONCURRENT_PAGES, 16)
            self.assertEqual(len(config.WATERMARK_PATTERNS), 1)
            self.assertEqual(config.WATERMARK_PATTERNS[0].width, 1000)
            self.assertEqual(config.WATERMARK_PATTERNS[0].height, 500)
        finally:
            # Clean up
            os.unlink(temp_path)
    
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


if __name__ == "__main__":
    unittest.main()
