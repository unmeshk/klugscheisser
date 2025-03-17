# Klugbot Database Import Tool

A command-line utility for recursively importing files from a directory into Klug-bot's knowledge database.

## Overview

This tool recursively scans a specified directory for files with selected formats, processes their content, and imports them into a knowledge database. It adds source URLs based on a provided prefix.

**Note**: Getting the source url to work correctly can be tricky. While it doesn't affect knowledge retrieval, it does affect the metadata that is retrieved and shown along with the knowledge.

## Prerequisites
- Python 3.7+
- Required packages (install via `pip install -r requirements.txt`):
  - python-dotenv
  - Any other dependencies needed for processing specific file formats

## Environment Setup

Create a `.env` file in the project root with any environment variables required for your knowledge database connection.

## Usage

```bash
python add_to_db.py --directory PATH_TO_DIRECTORY --formats FORMAT1,FORMAT2,... --url-prefix URL_PREFIX [--user-id USER_ID]
```

### Arguments

| Argument | Short Flag | Required | Description | Default |
|----------|------------|----------|-------------|---------|
| `--directory` | `-d` | Yes | Directory to process recursively | N/A |
| `--formats` | `-f` | Yes | Comma-separated list of file formats to process | N/A |
| `--url-prefix` | `-u` | Yes | URL prefix to add to file paths metadata for source URLs | N/A |
| `--user-id` | N/A | No | Slack User ID metadata to use as creator | `LOCAL_IMPORT` |

### Example

```bash
python add_to_db.py --directory ./documents --formats txt,md,pdf --url-prefix https://docs.example.com/ --user-id U0123456789
```

This command will:
1. Recursively scan the `./documents` directory
2. Process all `.txt`, `.md`, and `.pdf` files
3. Create source URLs by appending the relative file path to `https://docs.example.com/`
4. Set `U0123456789` as the creator ID for all imported content

## Output

The tool will provide a summary of the import process, including:
- Total files found
- Successfully processed files
- Failed files
- Total chunks extracted
- Successfully stored chunks
- Failed chunks

## Examples

### Basic Usage

```bash
python add_to_db.py -d ./content -f md,txt -u https://knowledge-base.internal/
```

### Specifying User ID

```bash
python add_to_db.py -d ./content -f md,txt,pdf,csv,json -u https://docs.company.com/ --user-id U0123456789
```

### Processing Diverse Formats

```bash
python add_to_db.py -d ./knowledge-base -f txt,md,mdx,rst,pdf,csv,json -u https://kb.example.org/
```

## Troubleshooting

- If the import fails, check that the specified directory exists
- Ensure your `.env` file contains all necessary environment variables
- Verify that you have the necessary dependencies for processing the specified file formats