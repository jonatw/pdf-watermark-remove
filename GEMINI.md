# GEMINI.md - Context & Knowledge Base

## Project Summary

**Project Name:** PDF Watermark Remover
**Primary Language:** Python
**Type:** CLI Tool & Web Service (Flask)

This project provides a robust solution for detecting and removing watermarks (both image and text-based) from PDF documents. It exposes its functionality through two primary interfaces:
1.  **CLI (`cli.py`):** For local, scriptable, and batch processing.
2.  **Web Server (`server.py`):** A Flask-based web application providing a UI and REST endpoints for remote usage.

The core logic is unified in `remove_watermark.py`, ensuring consistent behavior across both interfaces.

## Architecture Decisions

### Tech Stack
-   **Core Library:** `PyMuPDF` (pymupdf) for low-level PDF analysis and manipulation.
-   **Web Framework:** `Flask` (with `Werkzeug`).
-   **Configuration:** `PyYAML` for config files, supplemented by Environment Variables.
-   **Utilities:** `tqdm` for CLI progress bars.

### System Architecture
-   **Shared Kernel:** The `remove_watermark.py` module acts as the single source of truth for business logic, utilized by both the CLI and Server. This prevents logic drift.
-   **Strategy Pattern:** Watermark removal strategies (e.g., specific text patterns or image analysis) are encapsulated in `strategies.py`.
-   **State Management (Server):** The server generates a unique Job ID (UUID) for each upload to track processing status, stored in-memory (note: strictly in-memory for this version, non-persistent).
-   **Concurrency:**
    -   CLI supports parallel processing for batch operations.
    -   Server handles requests via standard Flask threading (development) or WSGI container (production ready).

### Key Models & Data Structures
-   **`WatermarkRemover`:** Main class orchestrating the removal process.
-   **`Config`:** Singleton/Module-level configuration loader handling defaults, YAML, and Env vars.
-   **`PDFProcessingError` / `InvalidPDFError`:** Custom exception hierarchy defined in `exceptions.py`.

## Business Logic

### Workflow
1.  **Input:** User provides a PDF path (CLI) or uploads a file (Web).
2.  **Validation:** File integrity and type are checked using `PyMuPDF`.
3.  **Strategy Selection:** The system iterates through configured strategies (Text/Image) to identify watermark artifacts.
4.  **Removal:**
    -   **Text:** Scans content streams for text matching specific patterns/coordinates.
    -   **Image:** Identifies and deletes XObjects referenced as watermarks.
5.  **Output:** A clean PDF is generated. The server provides a download link; CLI saves to disk.

### Management Commands (CLI)
-   **Single File:** `python cli.py input.pdf`
-   **Batch/Recursive:** `python cli.py ./folder/ --recursive`
-   **Custom Config:** `python cli.py input.pdf --config my_config.yaml`
-   **Server Start:** `python server.py` (Default: http://localhost:5566)

## Critical Notes

-   **Dependencies:** Requires `PyMuPDF`. Ensure C dependencies for MuPDF are satisfied if compiling from source, though wheels are standard.
-   **Temp Files:** The server relies on a temporary directory (default `data/` or system temp) to store uploads and processed files. Cleanup routines are essential for long-running instances.
-   **Testing:** Comprehensive tests in `tests.py` and `test_pdf.py`. Run via `python -m unittest tests.py`.
-   **Logging:** Centralized logging in `logging_utils.py` with rotation support.

## Tips for Gemini (CLI Acceleration Tools)

When interacting with this codebase, prioritize using the following high-performance CLI tools for speed and efficiency:

1.  **Searching Content:** `rg` (ripgrep)
    *   *Usage:* `rg "pattern" .` (Recursive search, significantly faster than `grep`)
    *   *Usage:* `rg -t py "class Watermark"` (Search only Python files)

2.  **Finding Files:** `fd`
    *   *Usage:* `fd pattern` (User-friendly alternative to `find`)
    *   *Usage:* `fd -e py` (Find all Python files)

3.  **Viewing Content:** `bat`
    *   *Usage:* `bat filename` (Syntax highlighting and git integration)

4.  **Listing Files:** `eza`
    *   *Usage:* `eza -l --icons` (Modern replacement for `ls`)
    *   *Usage:* `eza --tree` (View directory tree)

5.  **JSON Processing:** `jq`
    *   *Usage:* `cat config.json | jq .` (Pretty print and query JSON data)
