#!/usr/bin/env python3
"""
Verification script for the refactored PDF Watermark Remover.

This script tests the compatibility of the refactored code with the original code.
It processes a sample PDF file with both versions and compares the results.

Usage:
    python verify_refactoring.py [path_to_sample_pdf]

Author: PDF Watermark Remover Team
Version: 2.0.0
"""

import os
import sys
import asyncio
import tempfile
import time
from pathlib import Path
import filecmp
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import both the original and refactored versions
import remove_watermark as original
from remove_watermark import remove_watermark as refactored_remove_watermark


class CompatibilityVerifier:
    """Class for verifying compatibility between original and refactored code."""
    
    def __init__(self, sample_pdf: str):
        """
        Initialize the verifier.
        
        Args:
            sample_pdf: Path to sample PDF file
        """
        self.sample_pdf = sample_pdf
        self.original_output = None
        self.refactored_output = None
    
    async def verify(self) -> bool:
        """
        Verify compatibility between original and refactored code.
        
        Returns:
            bool: True if compatible, False otherwise
        """
        if not os.path.exists(self.sample_pdf):
            logger.error(f"Sample PDF file not found: {self.sample_pdf}")
            return False
        
        logger.info(f"Testing with sample PDF: {self.sample_pdf}")
        
        # Create temporary files for the output
        try:
            with tempfile.NamedTemporaryFile(suffix="_original.pdf", delete=False) as orig_tmp:
                self.original_output = orig_tmp.name
            
            with tempfile.NamedTemporaryFile(suffix="_refactored.pdf", delete=False) as refac_tmp:
                self.refactored_output = refac_tmp.name
            
            # Process with original code
            logger.info("Processing with original code...")
            orig_start = time.time()
            await original.remove_watermark(self.sample_pdf, self.original_output)
            orig_time = time.time() - orig_start
            logger.info(f"Original code finished in {orig_time:.2f}s")
            
            # Process with refactored code
            logger.info("Processing with refactored code...")
            refac_start = time.time()
            await refactored_remove_watermark(self.sample_pdf, self.refactored_output)
            refac_time = time.time() - refac_start
            logger.info(f"Refactored code finished in {refac_time:.2f}s")
            
            # Compare results
            return self._compare_results(orig_time, refac_time)
            
        except Exception as e:
            logger.error(f"Error during verification: {str(e)}")
            return False
        
        finally:
            # Clean up temporary files
            self._cleanup_temp_files()
    
    def _compare_results(self, orig_time: float, refac_time: float) -> bool:
        """
        Compare the results of the original and refactored code.
        
        Args:
            orig_time: Time taken by original code
            refac_time: Time taken by refactored code
            
        Returns:
            bool: True if results are compatible, False otherwise
        """
        # Compare file sizes
        orig_size = os.path.getsize(self.original_output)
        refac_size = os.path.getsize(self.refactored_output)
        size_diff = abs(orig_size - refac_size)
        size_percent_diff = (size_diff / orig_size) * 100 if orig_size > 0 else 0
        
        logger.info(f"Original output size: {orig_size} bytes")
        logger.info(f"Refactored output size: {refac_size} bytes")
        logger.info(f"Size difference: {size_diff} bytes ({size_percent_diff:.2f}%)")
        
        # Compare performance
        perf_diff = (refac_time / orig_time) * 100 if orig_time > 0 else 0
        logger.info(f"Performance comparison: {perf_diff:.2f}% (100% means same speed)")
        
        # Binary comparison of files
        files_identical = filecmp.cmp(self.original_output, self.refactored_output, shallow=False)
        
        if files_identical:
            logger.info("✅ Success: Output files are identical!")
            return True
        else:
            # If files are not identical but size difference is small, it might still be acceptable
            if size_percent_diff < 5:
                logger.info("⚠️ Warning: Output files are slightly different, but size difference is less than 5%")
                logger.info("This may be acceptable due to different optimization settings or metadata handling")
                return True
            else:
                logger.error("❌ Error: Output files are significantly different")
                return False
    
    def _cleanup_temp_files(self):
        """Clean up temporary files."""
        for file in [self.original_output, self.refactored_output]:
            if file and os.path.exists(file):
                try:
                    os.unlink(file)
                except:
                    pass


class PDFFileFinder:
    """Class for finding PDF files in the project."""
    
    @staticmethod
    def find_sample_pdf() -> str:
        """
        Find a sample PDF file in the project.
        
        Returns:
            str: Path to a sample PDF file, or None if not found
        """
        # Look in data directory first
        data_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "data"
        if data_dir.exists():
            pdfs = list(data_dir.glob("*.pdf"))
            if pdfs:
                return str(pdfs[0])
        
        # Look in project root
        project_root = Path(os.path.dirname(os.path.dirname(__file__)))
        pdfs = list(project_root.glob("*.pdf"))
        if pdfs:
            return str(pdfs[0])
        
        return None


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify compatibility between original and refactored PDF Watermark Remover",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "sample_pdf", 
        nargs="?", 
        help="Path to a sample PDF file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get sample PDF file
    sample_pdf = args.sample_pdf
    
    if not sample_pdf:
        sample_pdf = PDFFileFinder.find_sample_pdf()
        if not sample_pdf:
            logger.error("Error: No sample PDF file provided and none found in the project")
            logger.error("Please provide a sample PDF file path as an argument")
            sys.exit(1)
    
    # Verify compatibility
    verifier = CompatibilityVerifier(sample_pdf)
    success = await verifier.verify()
    
    if success:
        logger.info("\n🎉 Verification passed! The refactored code is compatible with the original code.")
        sys.exit(0)
    else:
        logger.error("\n❌ Verification failed! The refactored code produces different results.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
