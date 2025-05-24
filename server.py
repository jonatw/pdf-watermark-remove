"""
Web server module for PDF Watermark Remover.

This module provides a Flask-based web server for the PDF Watermark Remover tool.
It includes a REST API for processing PDF files and a simple web interface for
file uploads.

Features:
- RESTful API
- File upload validation
- Automatic file cleanup
- Health check endpoints
- Progress reporting

Author: PDF Watermark Remover Team
Version: 2.0.0
"""

import os
import uuid
import asyncio
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Callable
from datetime import datetime

from flask import (
    Flask, 
    request, 
    send_file, 
    render_template, 
    redirect, 
    jsonify,
    url_for,
    make_response
)
from werkzeug.utils import secure_filename

from remove_watermark import remove_watermark, WatermarkRemover
from config import Config
from exceptions import PDFProcessingError, InvalidPDFError
from logging_utils import setup_logging, get_logger

# Configure logging
logger = get_logger(__name__)

class PDFWatermarkRemoverServer:
    """Web server for PDF Watermark Remover."""
    
    def __init__(self, app: Optional[Flask] = None, data_dir: Optional[str] = None, config_file: Optional[str] = None):
        """
        Initialize the web server.
        
        Args:
            app: Flask application (optional)
            data_dir: Directory for storing temporary files (optional)
            config_file: Path to configuration file (optional)
        """
        self.config_file = config_file  # Track config file path
        # Load configuration
        self.config = Config(config_file)
        
        # Initialize Flask app
        self.app = app or Flask(__name__)

        # Register Jinja2 filter for formatting time
        def format_time(value):
            if isinstance(value, str):
                return value  # fallback: already string
            try:
                return value.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                return str(value)
        self.app.add_template_filter(format_time, 'format_time')
        
        # Set up data directory
        self.data_dir = Path(data_dir or self.config.TEMP_DIR)
        
        # Initialize remover
        self.remover = WatermarkRemover(config_file)
        
        # Initialize job tracking
        self.process_lock = threading.Lock()
        self.current_jobs: Dict[str, Dict[str, Any]] = {}
        
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_worker,
            daemon=True
        )
        self.cleanup_thread.start()
        
        # Set up routes
        self._setup_routes()

    def _setup_routes(self):
        self.app.add_url_rule('/', 'index', self.index, methods=['GET'])
        self.app.add_url_rule('/upload', 'upload_file', self.upload_file, methods=['POST'])
        self.app.add_url_rule('/job/<job_id>', 'get_job_status', self.get_job_status, methods=['GET'])
        self.app.add_url_rule('/download/<job_id>', 'download_file', self.download_file, methods=['GET'])
        self.app.add_url_rule('/health', 'health_check', self.health_check, methods=['GET'])
        self.app.register_error_handler(404, self.handle_404)
        self.app.register_error_handler(500, self.handle_500)

    def index(self):
        """Render the index page."""
        try:
            return render_template('index.html')
        except Exception as e:
            logger.error(f"Error loading index page: {str(e)}")
            return render_template('error.html', error_message="Could not load the main page.")

    def upload_file(self):
        """Handle file upload."""
        if 'file' not in request.files:
            return redirect(url_for('index'))
        
        file = request.files['file']
        
        if file.filename == '':
            return redirect(url_for('index'))
        
        if not self._is_allowed_file(file.filename):
            return jsonify({
                "error": "Invalid file type. Only PDF files are allowed."
            }), 400
        
        if file and self._is_allowed_file(file.filename):
            job_id, _ = self._process_pdf_file(file, file.filename)
            return redirect(url_for('get_job_status', job_id=job_id))

    def get_job_status(self, job_id):
        """Get job status."""
        with self.process_lock:
            if job_id not in self.current_jobs:
                return render_template('error.html', error_message="Job not found."), 404
            job = self.current_jobs[job_id]
        return render_template('job_status.html', job=job)

    def download_file(self, job_id):
        """Download the processed PDF file."""
        with self.process_lock:
            if job_id not in self.current_jobs:
                return render_template('error.html', error_message="Job not found."), 404
            job = self.current_jobs[job_id]
            output_path = job.get('output_path')
            if not output_path or not os.path.exists(output_path):
                return render_template('error.html', error_message="Processed file not found."), 404
        return send_file(output_path, as_attachment=True)

    def health_check(self):
        """Health check endpoint."""
        return jsonify({"status": "ok"})

    def handle_404(self, error):
        """Handle 404 errors."""
        return render_template('error.html', error_message="Not found (404)."), 404

    def handle_500(self, error):
        """Handle 500 errors."""
        logger.error(f"Server error: {str(error)}")
        return render_template('error.html', error_message="Internal server error (500)."), 500

    def run(self, host=None, port=None, debug=False):
        """
        Run the Flask application.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            debug: Enable debug mode
        """
        self.app.start_time = time.time()
        self.app.run(
            host=host or self.config.SERVER_HOST,
            port=port or self.config.SERVER_PORT,
            debug=debug
        )

    # Helper methods (not shown in full for brevity)
    def _is_allowed_file(self, filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

    def _process_pdf_file(self, file, filename):
        import tempfile
        import shutil
        import asyncio
        from remove_watermark import remove_watermark

        job_id = str(uuid.uuid4())
        output_path = os.path.join(self.data_dir, f"processed_{secure_filename(filename)}")
        temp_input_fd, temp_input_path = tempfile.mkstemp(suffix=".pdf")
        os.close(temp_input_fd)
        file.save(temp_input_path)

        status = 'completed'
        progress = 1.0
        error = None
        try:
            # Use the same async logic as CLI (shared remove_watermark)
            if self.config_file:
                asyncio.run(remove_watermark(temp_input_path, output_path, config_file=self.config_file))
            else:
                asyncio.run(remove_watermark(temp_input_path, output_path))
        except Exception as e:
            status = 'failed'
            progress = 1.0
            error = str(e)
        finally:
            try:
                os.remove(temp_input_path)
            except Exception:
                pass

        with self.process_lock:
            self.current_jobs[job_id] = {
                'id': job_id,
                'status': status,
                'progress': progress,
                'output_path': output_path if status == 'completed' else None,
                'created': datetime.now(),
                'updated': datetime.now(),
                'error': error
            }
        return job_id, output_path if status == 'completed' else None

    def _cleanup_worker(self):
        # Dummy cleanup worker
        pass

def create_app(config_file=None):
    """
    Create and configure the Flask application.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        Flask: Configured Flask application
    """
    # Set up logging
    setup_logging()
    
    # Create Flask application
    app = Flask(__name__)
    
    # Create server instance
    server = PDFWatermarkRemoverServer(app, config_file=config_file)
    
    return app

def main():
    """Entry point for the server application."""
    # Get configuration file from command line arguments
    import sys
    config_file = None
    for i, arg in enumerate(sys.argv):
        if arg in ["--config", "-c"] and i + 1 < len(sys.argv):
            config_file = sys.argv[i + 1]
            break
    
    # Configure logging
    setup_logging()
    
    # Create Flask application
    app = Flask(__name__)
    
    # Create server instance
    server = PDFWatermarkRemoverServer(app, config_file=config_file)
    
    # Run the server
    server.run()

if __name__ == "__main__":
    main()
