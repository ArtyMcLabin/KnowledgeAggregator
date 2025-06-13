# Knowledge Aggregator

A tool for aggregating and processing knowledge from various sources into a unified knowledge base.

## Overview

Knowledge Aggregator is a Python-based tool designed to collect information from various sources such as:

- Trello boards
- Google Sheets
- Supabase databases
- Git repositories

The collected information is processed and stored in a structured format, making it easier to analyze and utilize the knowledge across different projects.

## Features

- Connect to and retrieve data from Trello boards
- Export and process Google Sheets data
- Extract schema information from Supabase databases
- Process Git repositories using repomix
- Create a unified knowledge base from multiple sources
- Customizable output formats and directories

## Installation

1. Clone this repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Copy `env.example` to `.env` and fill in your API credentials

## Usage

Run the knowledge aggregator with a profile:

```bash
python knowledge_aggregator.py --profile projectsSources/your_profile.json
```

### Profile Configuration

Create a JSON profile with your data sources:

```json
{
  "name": "Project Name",
  "output_dir": "knowledge_base_output/Project_Name",
  "trello": {
    "boards": [
      {"id": "board_id"}
    ]
  },
  "google_sheets": [
    {"id": "sheet_id"}
  ],
  "supabase": {
    "url": "your_supabase_url",
    "key": "your_supabase_key"
  },
  "repositories": [
    {"path": "path/to/local/repo"}
  ]
}
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Setup

1.  **Install Dependencies**:
    *   Ensure you have [Node.js](https://nodejs.org/) installed (for `npx`).
    *   Ensure you have the [PostgreSQL client](https://www.postgresql.org/download/) installed (for `pg_dump`).
    *   Install Python packages:
        ```bash
        pip install -r requirements.txt
        ```

2.  **Configure Environment File**:
    *   Copy `new.env` to a new file named `.env`.
        ```bash
        # On Windows
        copy new.env .env
        # On macOS/Linux
        cp new.env .env
        ```
    *   Fill in your personal credentials (Trello API key/token) in the `.env` file.
    *   Make sure the `GOOGLE_CLIENT_SECRETS_JSON` variable points to your downloaded credentials file.

3.  **Set up Google Authentication**:
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
    *   Create or select a project.
    *   Create an "OAuth 2.0 Client ID" for a "Desktop app".
    *   Download the client secrets JSON file and place it in the `auth/` directory.
    *   Update the `GOOGLE_CLIENT_SECRETS_JSON` path in your `.env` file to point to this file.
    *   The first time you run the script, it will open a browser window for you to authorize access. A `token.json` file will be created in the `auth/` directory to store your authorization.

4.  **Create a Project Profile**:
    *   Inside the `projectsSources/` directory, create a JSON file for your project (e.g., `my_project.json`).
    *   Use `projectsSources/wa_assistant.json` as a template.
    *   Define all the data sources for your project in this file.
    *   **Database Credentials**: For simplicity and project portability, database credentials (`host`, `user`, `password`, etc.) are stored directly in the project's JSON profile.

## Output

The script generates the following files in the output directory:

- `trello_board_data.json`: JSON data from your Trello board
- `google_sheet_export.csv`: CSV export of your Google Sheet
- `supabase_schema.sql`: SQL schema of your Supabase database
- `repo_*_collapsed.txt`: Collapsed text files of your local repositories

## Security Notes

*   The `.gitignore` file is configured to exclude sensitive files like `.env`, `*.json` credential files, and the `projectsSources/` directory. **Do not commit them to version control.**
*   Keep personal API keys and tokens in your local `.env` file. Project-specific credentials, like database connection details, are stored in the JSON profiles within the `projectsSources` directory.

# Knowledge Aggregator

A Python script that aggregates knowledge from various sources for use with LLMs. This script fetches data from:

- Trello boards
- Google Sheets
- Supabase databases
- Local Git repositories

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Configure environment variables:
   - Copy `env.example` to `.env`
   - Fill in your API keys, tokens, and other credentials

3. For Google Sheets access:
   - Create a service account in Google Cloud Console
   - Download the JSON credentials file
   - Place it in your project directory or specify the path in `.env`
   - Share your Google Sheet with the service account email

4. For Supabase access:
   - Ensure you have PostgreSQL client (pg_dump) installed
   - Get your database credentials from Supabase dashboard

## Usage

Run the script:

```
python knowledge_aggregator.py
```

Optional arguments:
- `-o, --output`: Specify the output directory (default: `knowledge_base_output`)

## Output

The script generates the following files in the output directory:

- `trello_board_data.json`: JSON data from your Trello board
- `google_sheet_export.csv`: CSV export of your Google Sheet
- `supabase_schema.sql`: SQL schema of your Supabase database
- `repo_*_collapsed.txt`: Collapsed text files of your local repositories

## Security Notes

- Never commit your `.env` file or any credentials to version control
- The `.gitignore` file is configured to exclude sensitive files
- API keys and tokens should be kept private 