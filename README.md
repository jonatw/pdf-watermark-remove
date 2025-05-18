# PDF Watermark Remover

This project provides tools to remove watermarks from PDF files. It includes both a web server for processing PDF uploads and a command-line interface (CLI) for local file processing.

## Features

* **Dual Interface:** Offers both a web server and a CLI for flexibility.
* **Adaptive Watermark Removal:** Employs two distinct strategies to remove watermarks based on PDF metadata and content analysis.
* **Dockerized Server:** The server component can be easily deployed using Docker.

## How It Works: Watermark Removal Strategies

The core watermark removal logic dynamically chooses a strategy based on the PDF's metadata.

1.  **XRef Image Removal:**
    * **Trigger:** Activated if the `producer` field in the PDF's metadata contains the string "Version".
    * **Algorithm:**
        1.  Scans images on the first page of the PDF.
        2.  Identifies potential watermark images by matching their dimensions to common watermark sizes (2360×1640 or 1640×2360 pixels).
        3.  Deletes the identified image using its Cross-Reference (XRef) ID.
        4.  Saves the modified document.
    * **Pros:** Fast and highly effective for image-based watermarks with known, fixed dimensions.
    * **Cons:** Limited to image watermarks that match the predefined dimensions.

2.  **Common String Removal:**
    * **Trigger:** Used if the conditions for XRef Image Removal are not met.
    * **Algorithm:**
        1.  Reads the content stream of the first page.
        2.  Identifies the most frequently occurring substring (default length: 100 characters) that follows the pattern `b" Td\n<"`. This pattern is often associated with text-based watermarks.
        3.  Removes all instances of this identified substring from the content stream of each page. This process is parallelized for efficiency.
        4.  Saves the modified document.
    * **Pros:** Capable of removing text-based watermarks even if they are not defined as fixed-size images.
    * **Cons:** The effectiveness can depend on the chosen pattern and substring length. There's a potential risk of removing legitimate content if its structure coincidentally matches the watermark pattern.

## Code Structure

The project is organized into three main Python scripts:

* `server.py`: Implements the web server using Flask (or a similar framework) to handle PDF uploads and serve processed files.
* `cli.py`: Provides the command-line interface for direct PDF processing.
* `remove_watermark.py`: Contains the core logic for both watermark removal strategies. Both `server.py` and `cli.py` utilize this module.

```mermaid
flowchart TD
    subgraph CLI [cli.py]
        A["main()"] --> B["async_main()"]
        B --> C[/remove_watermark&#40;input, output&#41;/]
    end

    subgraph Server [server.py]
        D["index()"] --> E["upload_file()"]
        E --> C
    end

    subgraph Core [remove_watermark.py]
        C --> F{"'Version' in producer?"}
        F -- "Yes" --> G[/remove_watermark_by_xref&#40;&#41;/]
        F -- "No" --> H[/remove_watermark_by_common_str&#40;&#41;/]
        G --> I[/get_target_xref_at_first_page&#40;&#41;/]
        H --> J[/most_frequent_substring_with_pattern&#40;&#41;/]
        H --> K[/remove_watermark_from_page&#40;&#41;/]
    end
````

## Getting Started

Follow these steps to set up the project for local development or CLI usage.

### Prerequisites

  * Python 3.11 (Download from [python.org](https://www.python.org/downloads/) if not installed)

### Local Development Setup

1.  **Clone the repository (if you haven't already):**

    ```bash
    git clone git@github.com:jonatw/pdf-watermark-remove.git
    cd pdf-watermark-remove
    ```

2.  **Create a virtual environment:**
    This isolates project dependencies.

    ```bash
    python3 -m venv .venv
    ```

3.  **Activate the virtual environment:**

      * On macOS and Linux:
        ```bash
        source .venv/bin/activate
        ```
      * On Windows:
        ```bash
        .\.venv\Scripts\Activate
        ```

4.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

    You are now ready for local development or to use the CLI script.

## Usage

### Command-Line Interface (CLI)

The CLI script processes a PDF file and saves the output in the same directory, appending "\_no\_watermark" to the original filename.

**Command:**

```bash
python cli.py <path_to_your_file.pdf>
```

**Example:**
If you have a file named `mydocument.pdf`, run:

```bash
python cli.py mydocument.pdf
```

This will generate a new file named `mydocument_no_watermark.pdf` in the same directory.

### Server (via Docker)

The server provides an endpoint to upload a PDF, which then returns the processed file.

1.  **Build the Docker image:**
    From the project's root directory, run:

    ```bash
    docker-compose build
    ```

2.  **Run the Docker container:**
    This command starts the server in detached mode.

    ```bash
    docker-compose up -d
    ```

3.  **Access the server:**

      * The server will be running at `http://127.0.0.1:5566`.
      * To process a file, send a POST request with the PDF file to the `/upload` endpoint (e.g., using a tool like Postman or a simple HTML form).
      * The server will respond with the watermark-removed PDF file.
