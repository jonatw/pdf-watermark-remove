#!/usr/bin/env python3
"""
Test script for PDF Watermark Remover.

This script provides a simple way to test the watermark removal functionality
on a specific PDF file. It uses the refactored code to process the file and
reports the result.

Usage:
    python test_pdf.py <pdf_file>

Author: PDF Watermark Remover Team
Version: 2.0.0
"""

import os
import sys
import asyncio
import time
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from the refactored_v2 package
from refactored_v2 import (
    remove_watermark,
    WatermarkRemover,
    Config,
    InvalidPDFError,
    PDFProcessingError
)


class PdfTester:
    """Class for testing PDF watermark removal."""
    
    def __init__(self, input_file: str):
        """
        Initialize the tester.
        
        Args:
            input_file: Path to input PDF file
        """
        self.input_file = input_file
        self.output_file = str(Path(input_file).with_suffix(".nowm.pdf"))
        self.start_time = None
        self.end_time = None
    
    async def run_test(self) -> bool:
        """
        Run the watermark removal test.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"Testing watermark removal on: {self.input_file}")
            print(f"Output will be saved to: {self.output_file}")
            print("-" * 50)
            
            # Create a remover instance
            remover = WatermarkRemover()
            
            # Track time
            self.start_time = time.time()
            
            # Process file with progress callback
            success = await remover.remove_watermark(
                self.input_file,
                self.output_file,
                self._progress_callback
            )
            
            self.end_time = time.time()
            
            # Print result
            if success:
                print("\n✅ Successfully removed watermark!")
            else:
                print("\n⚠️ No watermark found or removal failed")
            
            # Print processing time
            elapsed = self.end_time - self.start_time
            print(f"Processing time: {elapsed:.2f} seconds")
            
            return success
            
        except InvalidPDFError as e:
            print(f"\n❌ Invalid PDF: {str(e)}")
            return False
        except PDFProcessingError as e:
            print(f"\n❌ Processing error: {str(e)}")
            return False
        except Exception as e:
            print(f"\n❌ Unexpected error: {str(e)}")
            return False
    
    def _progress_callback(self, status: str):
        """
        Progress callback function.
        
        Args:
            status: Status message
        """
        print(f"\rStatus: {status}", end="")


async def main():
    """Main entry point."""
    # Check arguments
    if len(sys.argv) < 2:
        print("Usage: test_pdf.py <pdf_file>")
        return 1
    
    # Get input file
    input_file = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        return 1
    
    # Check if file is a PDF
    if not input_file.lower().endswith(".pdf"):
        print(f"Error: File is not a PDF: {input_file}")
        return 1
    
    # Run test
    tester = PdfTester(input_file)
    success = await tester.run_test()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
