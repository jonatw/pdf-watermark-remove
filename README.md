# PDF Watermark Remover

Remove watermarks from PDF files, supporting both image-based and text-based watermarks. Provides a command-line interface (CLI) and a web service for batch and remote processing.

---

## Features

| Feature                                 | Description                                              |
|------------------------------------------|----------------------------------------------------------|
| Automatic Detection & Removal            | Detects and removes watermarks automatically             |
| Image & Text Watermark Support           | Handles both image and text watermarks                   |
| CLI & Web Service                        | Command-line and web UI for flexible usage               |
| Batch & Recursive Processing             | Batch process directories, with optional recursion       |
| Parallel Processing                      | Accelerate with multi-process parallelism                |
| Config File Support (YAML)               | Flexible configuration via YAML file                     |
| Progress Reporting                       | Detailed progress output                                 |
| Logging & Log Rotation                   | Console/file logging with rotation and filtering         |
| Robust Error Handling                    | Custom exceptions for various error scenarios            |
| Unit Tests                               | Comprehensive unit tests                                 |

---

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/pdf-watermark-remove.git
cd pdf-watermark-remove

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Usage

### Command-Line Interface

Basic usage:

```bash
python cli.py /path/to/your/document.pdf
```

This creates an output file named `document_no_watermark.pdf` in the same directory.

#### Advanced Options

```bash
python cli.py document.pdf --out output.pdf --config config.yaml
```

### Web Server

Start the server:

```bash
python server.py
```

Visit [http://localhost:5566](http://localhost:5566) in your browser to upload PDF files for watermark removal.

- **Job Status:** After upload, the web UI shows job progress and any errors encountered.
- **Unified Logic:** The server now uses the exact same watermark removal logic as the CLI (via `remove_watermark` in `remove_watermark.py`). There is no code duplication; all PDF processing is consistent across both interfaces.

#### Configuration

Both CLI and server accept a YAML config file for advanced options. The server will use the config file if specified at startup.

---

## Configuration & Environment Variables

| Variable                           | Description                                | Default         |
|-------------------------------------|--------------------------------------------|-----------------|
| PDF_WATERMARK_LOG_LEVEL             | Logging level                              | INFO            |
| PDF_WATERMARK_LOG_FILE              | Log file path                              | (none)          |
| PDF_WATERMARK_MAX_CONCURRENT_PAGES  | Max concurrent page processing             | 8               |
| PDF_WATERMARK_TEMP_DIR              | Temp file directory                        | data            |
| PDF_WATERMARK_SERVER_HOST           | Server host                                | 0.0.0.0         |
| PDF_WATERMARK_SERVER_PORT           | Server port                                | 5566            |
| PDF_WATERMARK_PARALLEL_PROCESSES    | Default parallel worker count              | 1               |

---

## Core Classes & Structure

| File/Class             | Purpose                                            |
|-----------------------|----------------------------------------------------|
| `remove_watermark.py` | Core watermark removal logic (shared by CLI/server)|
| `strategies.py`       | Watermark removal strategies (image/text)          |
| `config.py`           | Configuration management (YAML/env support)        |
| `exceptions.py`       | Custom exceptions                                  |
| `cli.py`              | Command-line interface                             |
| `server.py`           | Web service interface                              |
| `logging_utils.py`    | Logging utilities                                  |
| `test_pdf.py`         | PDF test utilities                                 |
| `tests.py`            | Unit tests                                         |
| `verify_refactoring.py`| Refactoring verification tools                     |

---

## License

MIT
