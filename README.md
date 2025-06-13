# Knowledge Aggregator

A Python script that aggregates knowledge from various sources for use with LLMs. This script fetches data from Trello, Google Sheets, Supabase databases, and local Git repositories based on project-specific profiles.

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

## Usage

Run the script from your terminal, specifying which profile you want to use:

```bash
python knowledge_aggregator.py --profile projectsSources/wa_assistant.json
```

*   You can create multiple profiles for different projects.
*   The output files will be saved in a subdirectory named after your project inside the `knowledge_base_output` folder.

### Optional Arguments

*   `-o, --output`: Specify a different main output directory (default: `knowledge_base_output`).

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