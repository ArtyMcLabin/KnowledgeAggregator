# v0.1 Knowledge Aggregator

This tool is designed to be set up and used by a Large Language Model (LLM) assistant like the one in Cursor. Point your LLM to this README file and instruct it to follow the setup steps.

## What it does

Knowledge Aggregator is a Python script that collects information from various sources and consolidates it into a structured knowledge base. It can connect to:

- Trello boards
- Google Sheets
- Supabase databases
- Local Git repositories

The output is a set of files that can be easily consumed by an LLM to understand the context of a project.

## ❗❗❗❗❗❗ LLM Assistant: Setup Instructions

Follow these steps to set up the project environment.

### 1. Install Dependencies

You'll need Node.js (for `npx`), the PostgreSQL client (`pg_dump`), and Python. Once those are installed, install the required Python packages:

```bash
pip install -r requirements.txt
```

### 2. Configure Environment File

1.  Copy the `env.example` file to a new file named `.env`.
2.  Open the `.env` file and fill in your personal API credentials (e.g., `TRELLO_API_KEY`, `TRELLO_TOKEN`).
3.  Make sure to set the `GOOGLE_CLIENT_SECRETS_JSON` variable, as explained in the next step.

### 3. Set up Google Authentication

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2.  Create or select a project.
3.  Create an **OAuth 2.0 Client ID** for a **Desktop app**.
4.  Download the client secrets JSON file.
5.  Place the downloaded file into the `auth/` directory (you may need to create this directory).
6.  Update the `GOOGLE_CLIENT_SECRETS_JSON` path in your `.env` file to point to this new file (e.g., `auth/your_credentials_file.json`).

When you run the script for the first time, it will open a browser window for you to authorize access. A `token.json` file will be created in the `auth/` directory to store your authorization for future runs.

### 4. Understand and Create Project Profiles

**What is a profile?**

A "profile" is a JSON configuration file that defines a specific project or startup you are working on. Each profile tells the Knowledge Aggregator which data sources to collect for that specific project.

You should create one profile for each distinct project. These profiles are stored in the `projectsSources/` directory.

**Create a profile:**

1.  Create a new JSON file inside the `projectsSources/` directory (e.g., `my_startup.json`).
2.  Use the example below as a template. Define all the data sources for your project in this file.

**Example Profile (`projectsSources/my_startup.json`):**

```json
{
  "name": "My Awesome Startup",
  "output_dir": "knowledge_base_output/My_Awesome_Startup",
  "trello": {
    "boards": [
      {"id": "your_trello_board_id"}
    ]
  },
  "google_sheets": [
    {"id": "your_google_sheet_id"}
  ],
  "supabase": {
    "db_host": "db.your-supabase-project.co",
    "db_user": "postgres",
    "db_password": "your-db-password",
    "db_name": "postgres",
    "db_port": 5432,
    "excluded_schemas": ["graphql", "graphql_public", "realtime", "storage", "pg_net"]
  },
  "repositories": [
    {"path": "C:/path/to/your/local/repo"}
  ]
}
```

## How to Run

To run the aggregator, you must specify a profile using the `--profile` command-line argument:

```bash
python knowledge_aggregator.py --profile projectsSources/my_startup.json
```

This command will process all the data sources defined in `my_startup.json` and place the output in the `knowledge_base_output/My_Awesome_Startup/` directory.

### Tip: Create a Wrapper Script

For convenience, you can create a simple wrapper script (e.g., `run_my_startup.bat` or `run_my_startup.sh`) to execute the command for a specific profile with a single click.

**Example (`run_my_startup.bat` on Windows):**
```bat
@echo off
python knowledge_aggregator.py --profile projectsSources/my_startup.json
pause
```

## Output

The script generates the following files in the profile's specified output directory:

- `trello_board_{id}.json`: JSON data from your Trello board.
- `google_sheet_{id}.csv`: CSV export of your Google Sheet.
- `supabase_schema.sql`: SQL schema of your Supabase database.
- `repo_{name}_repomix.txt`: Collapsed text files of your local repositories.

## Security Notes

- The `.gitignore` file is configured to exclude sensitive files like `.env`, `auth/` directory, and the `projectsSources/` directory. **Do not commit them to version control.**
- Keep personal API keys and tokens in your local `.env` file. Project-specific credentials, like database connection details, are stored in the JSON profiles within the `projectsSources` directory.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details. 