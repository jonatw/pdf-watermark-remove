# PDF Watermark Remover

This project contains two parts:

1. A server that provides an endpoint for uploading a PDF file, removes its watermark, and returns the processed file.
2. A command-line interface (CLI) script that removes the watermark from a PDF file.

## Server

The server can be built and run using Docker Compose. To do this, run the following commands in the terminal:

```
docker-compose build
docker-compose up -d
```

Once the server is running, it will be accessible at `127.0.0.1:5566`. You can also upload a PDF file to the `/upload` endpoint. The server will return the processed file.

## CLI

The CLI script takes a PDF file as an argument, removes its watermark, and saves the output in the same directory as the input file, appending "_no_watermark" to the original filename. To use the CLI script, run the following command in the terminal:

```
python cli.py <path_to_your_file.pdf>
```

Replace `<path_to_your_file.pdf>` with the path to the PDF file you want to process.

## Local Development

To set up the project for local development, follow these steps:

1. Ensure you have Python 3.11 installed. If not, download and install it from the [official Python website](https://www.python.org/downloads/).
2. Create a virtual environment in the project directory:

```
python3 -m venv .venv
```

3. Activate the virtual environment:

On Unix or MacOS, run:

```
source .venv/bin/activate
```

On Windows, run:

```
.venv\Scriptsctivate
```

4. Install the required packages:

```
pip install -r requirements.txt
```

You are now ready to start developing!
