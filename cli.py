"""
Command-line interface for PDF Watermark Remover.

This module provides a robust command-line interface for the PDF Watermark
Remover tool, supporting single file processing, batch processing, recursive
directory scanning, and parallel processing.

Usage:
    python cli.py <input_file> [options]
    python cli.py --batch <directory> [options]

Author: PDF Watermark Remover Team
Version: 2.0.0
"""

import os
import sys
import time
import asyncio
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

from config import Config
from exceptions import PDFProcessingError, InvalidPDFError
from logging_utils import setup_logging, get_logger
from remove_watermark import WatermarkRemover


# Configure logging
logger = get_logger(__name__)


class PDFWatermarkRemoverCLI:
    """Command-line interface for PDF Watermark Remover."""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the CLI.
        
        Args:
            config_file: Path to configuration file (optional)
        """
        self.config_file = config_file
        self.config = Config(config_file)
        self.remover = WatermarkRemover(config_file)
        self.args = None
        self.start_time = None
    
    def parse_arguments(self) -> argparse.Namespace:
        """
        Parse command-line arguments.
        
        Returns:
            argparse.Namespace: Parsed arguments
        """
        parser = argparse.ArgumentParser(
            description="PDF Watermark Remover - Remove watermarks from PDF files"
        )
        
        # Input specification
        input_group = parser.add_mutually_exclusive_group(required=True)
        input_group.add_argument(
            "input_file", 
            nargs="?", 
            help="Input PDF file to process"
        )
        input_group.add_argument(
            "--batch", "-b", 
            help="Process all PDF files in directory"
        )
        
        # Output options
        parser.add_argument(
            "--output", "-o",
            help="Output file path (for single file mode)"
        )
        parser.add_argument(
            "--output-dir", "-d",
            help="Output directory (for batch mode)"
        )
        
        # Processing options
        parser.add_argument(
            "--recursive", "-r",
            action="store_true",
            help="Recursively process subdirectories"
        )
        parser.add_argument(
            "--parallel", "-p",
            type=int,
            default=self.config.DEFAULT_PARALLEL_PROCESSES,
            help=f"Number of parallel processes (default: {self.config.DEFAULT_PARALLEL_PROCESSES})"
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing files"
        )
        parser.add_argument(
            "--backup",
            action="store_true",
            help="Create backup of original files"
        )
        
        # Configuration options
        parser.add_argument(
            "--config", "-c",
            help="Path to configuration file"
        )
        
        # Logging options
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Verbose output"
        )
        parser.add_argument(
            "--log-file", "-l",
            help="Log file path"
        )
        
        args = parser.parse_args()
        
        # If configuration file is specified, reload configuration
        if args.config and args.config != self.config_file:
            self.config_file = args.config
            self.config = Config(self.config_file)
            self.remover = WatermarkRemover(self.config_file)
        
        # Validate arguments
        self._validate_arguments(parser, args)
        
        self.args = args
        return args
    
    def _validate_arguments(self, parser: argparse.ArgumentParser, args: argparse.Namespace):
        """
        Validate command-line arguments.
        
        Args:
            parser: ArgumentParser instance
            args: Parsed arguments
            
        Raises:
            SystemExit: If arguments are invalid
        """
        if args.input_file and args.output_dir:
            parser.error("--output-dir can only be used with --batch")
        
        if args.batch and args.output and not args.output_dir:
            parser.error("--output can only be used with single file mode")
        
        if args.recursive and not args.batch:
            parser.error("--recursive can only be used with --batch")
        
        if args.parallel < 1:
            parser.error("--parallel must be at least 1")
        
        if args.batch and not os.path.isdir(args.batch):
            parser.error(f"Batch directory not found: {args.batch}")
        
        if args.input_file and not os.path.exists(args.input_file):
            parser.error(f"Input file not found: {args.input_file}")
    
    def configure_logging(self):
        """Configure logging based on command-line arguments."""
        log_level = "DEBUG" if self.args.verbose else self.config.LOG_LEVEL
        log_file = self.args.log_file or self.config.LOG_FILE
        
        setup_logging(log_level, log_file)
    
    def get_output_path(self, input_path: Path) -> Path:
        """
        Determine output path for a given input file.
        
        Args:
            input_path: Path to input file
            
        Returns:
            Path: Path to output file
        """
        if not self.args.batch and self.args.output:
            return Path(self.args.output)
        
        # For batch mode or default single file mode
        filename = input_path.stem + self.config.DEFAULT_OUTPUT_SUFFIX + input_path.suffix
        
        if self.args.batch and self.args.output_dir:
            output_dir = Path(self.args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            return output_dir / filename
        
        # Default: same directory as input
        return input_path.parent / filename
    
    def find_pdf_files(self, directory: str, recursive: bool = False) -> List[Path]:
        """
        Find all PDF files in a directory.
        
        Args:
            directory: Directory to search
            recursive: Whether to search recursively
            
        Returns:
            List[Path]: List of PDF file paths
        """
        directory_path = Path(directory)
        
        pdf_files = []
        
        if recursive:
            # Walk through directory recursively
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith(".pdf"):
                        pdf_files.append(Path(root) / file)
        else:
            # Non-recursive search
            pdf_files = [
                f for f in directory_path.iterdir()
                if f.is_file() and f.suffix.lower() == ".pdf"
            ]
        
        return pdf_files
    
    def _create_backup(self, input_file: Path) -> bool:
        """
        Create a backup of the input file.
        
        Args:
            input_file: Path to input file
            
        Returns:
            bool: True if backup was created, False otherwise
        """
        if not self.args.backup or not input_file.exists():
            return False
            
        backup_path = input_file.with_suffix(input_file.suffix + ".bak")
        if not backup_path.exists() or self.args.overwrite:
            import shutil
            shutil.copy2(input_file, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return True
            
        return False
    
    def _progress_callback(self, file_name: str):
        """
        Create a progress callback function for a specific file.
        
        Args:
            file_name: Name of the file being processed
            
        Returns:
            callable: Progress callback function
        """
        def callback(status: str, progress: float):
            if self.args.verbose:
                progress_str = f"{progress * 100:.1f}%" if progress >= 0 else ""
                print(f"\r{file_name}: {status} {progress_str}", end="")
        
        return callback
    
    async def process_single_file(
        self, 
        input_file: Path, 
        output_file: Path, 
        show_progress: bool = True
    ) -> bool:
        """
        Process a single PDF file.
        
        Args:
            input_file: Path to input file
            output_file: Path to output file
            show_progress: Whether to show progress
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create backup if requested
            self._create_backup(input_file)
            
            # Check if output file exists
            if output_file.exists() and not self.args.overwrite:
                logger.warning(f"Output file exists, skipping: {output_file}")
                return False
            
            # Process file
            progress_callback = self._progress_callback(input_file.name) if show_progress else None
            
            success = await self.remover.remove_watermark(
                str(input_file),
                str(output_file),
                progress_callback
            )
            
            if show_progress:
                print("")  # Print newline after progress output
            
            if success:
                logger.info(f"Successfully processed: {input_file} -> {output_file}")
            else:
                logger.warning(f"No watermark found in: {input_file}")
            
            return success
            
        except InvalidPDFError as e:
            logger.error(f"Invalid PDF: {input_file} - {str(e)}")
            return False
        except PDFProcessingError as e:
            logger.error(f"Processing error: {input_file} - {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {input_file} - {str(e)}")
            return False
    
    async def process_batch(self, files: List[Path]) -> Dict[str, Any]:
        """
        Process a batch of PDF files.
        
        Args:
            files: List of input file paths
            
        Returns:
            Dict[str, Any]: Summary of processing results
        """
        results = {
            "total": len(files),
            "success": 0,
            "skipped": 0,
            "failed": 0,
            "start_time": time.time()
        }
        
        if not files:
            logger.warning("No PDF files found to process")
            return results
        
        # Determine processing approach
        if self.args.parallel > 1:
            await self._process_parallel(files, results)
        else:
            await self._process_sequential(files, results)
        
        results["end_time"] = time.time()
        results["total_time"] = results["end_time"] - results["start_time"]
        
        return results
    
    async def _process_sequential(self, files: List[Path], results: Dict[str, Any]):
        """
        Process files sequentially.
        
        Args:
            files: List of input file paths
            results: Results dictionary to update
        """
        logger.info(f"Processing {len(files)} files sequentially")
        
        # Show progress if tqdm is available
        if TQDM_AVAILABLE and not self.args.verbose:
            for file in tqdm(files, desc="Processing files"):
                output_file = self.get_output_path(file)
                if await self.process_single_file(file, output_file, False):
                    results["success"] += 1
                else:
                    results["skipped"] += 1
        else:
            # Process without progress bar
            for file in files:
                output_file = self.get_output_path(file)
                if await self.process_single_file(file, output_file, True):
                    results["success"] += 1
                else:
                    results["skipped"] += 1
    
    async def _process_parallel(self, files: List[Path], results: Dict[str, Any]):
        """
        Process files in parallel.
        
        Args:
            files: List of input file paths
            results: Results dictionary to update
        """
        from concurrent.futures import ProcessPoolExecutor
        from functools import partial
        
        logger.info(f"Processing {len(files)} files with {self.args.parallel} workers")
        
        # Create output paths
        output_files = [self.get_output_path(f) for f in files]
        
        # Create partial function for ProcessPoolExecutor
        from remove_watermark import remove_watermark
        process_func = partial(
            remove_watermark,
            config_file=self.config_file
        )
        
        # Process files in parallel
        with ProcessPoolExecutor(max_workers=self.args.parallel) as executor:
            tasks = [
                asyncio.create_task(
                    asyncio.to_thread(
                        process_func,
                        str(input_file),
                        str(output_file)
                    )
                )
                for input_file, output_file in zip(files, output_files)
            ]
            
            # Show progress if tqdm is available
            if TQDM_AVAILABLE:
                for task in tqdm(
                    asyncio.as_completed(tasks),
                    total=len(tasks),
                    desc="Processing files"
                ):
                    try:
                        if await task:
                            results["success"] += 1
                        else:
                            results["skipped"] += 1
                    except Exception:
                        results["failed"] += 1
            else:
                # Process without progress bar
                for task in asyncio.as_completed(tasks):
                    try:
                        if await task:
                            results["success"] += 1
                        else:
                            results["skipped"] += 1
                    except Exception:
                        results["failed"] += 1
    
    def print_summary(self, results: Dict[str, Any]):
        """
        Print processing summary.
        
        Args:
            results: Processing results
        """
        print("\n" + "=" * 50)
        print("Processing Summary")
        print("=" * 50)
        print(f"Total files:      {results['total']}")
        print(f"Successful:       {results['success']}")
        print(f"Failed:           {results['failed']}")
        print(f"Skipped:          {results['skipped']}")
        
        if "total_time" in results:
            total_time = results["total_time"]
            avg_time = total_time / results["total"] if results["total"] > 0 else 0
            print(f"Total time:       {total_time:.2f}s")
            print(f"Average time:     {avg_time:.2f}s per file")
        
        print("=" * 50)
    
    async def run(self):
        """Run the CLI application."""
        try:
            self.start_time = time.time()
            
            # Parse command-line arguments
            self.parse_arguments()
            
            # Configure logging
            self.configure_logging()
            
            # Print welcome message
            print(f"PDF Watermark Remover v{self.config.VERSION}")
            print("=" * 50)
            
            # Process files
            if self.args.batch:
                await self._run_batch_mode()
            else:
                await self._run_single_file_mode()
            
            return 0
            
        except KeyboardInterrupt:
            logger.info("Operation cancelled by user")
            return 1
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            if self.args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    async def _run_batch_mode(self):
        """Run in batch mode."""
        # Find PDF files
        pdf_files = self.find_pdf_files(
            self.args.batch,
            self.args.recursive
        )
        
        if not pdf_files:
            logger.error("No PDF files found in the specified directory")
            return
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        # Process files
        results = await self.process_batch(pdf_files)
        
        # Print summary
        self.print_summary(results)
    
    async def _run_single_file_mode(self):
        """Run in single file mode."""
        input_file = Path(self.args.input_file)
        output_file = self.get_output_path(input_file)
        
        print(f"Processing: {input_file}")
        
        success = await self.process_single_file(input_file, output_file)
        
        # Simple summary for single file
        if success:
            print(f"✅ Successfully processed: {input_file} -> {output_file}")
        else:
            print(f"⚠ No watermark found: {input_file}")
        
        # Print processing time
        elapsed = time.time() - self.start_time
        print(f"Processing time: {elapsed:.2f}s")


async def async_main():
    """Async entry point for the CLI application."""
    # Get configuration file from command line arguments
    import sys
    config_file = None
    for i, arg in enumerate(sys.argv):
        if arg in ["--config", "-c"] and i + 1 < len(sys.argv):
            config_file = sys.argv[i + 1]
            break
    
    # Create CLI instance with configuration
    cli = PDFWatermarkRemoverCLI(config_file)
    exit_code = await cli.run()
    sys.exit(exit_code)


def main():
    """Entry point for the CLI application."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
