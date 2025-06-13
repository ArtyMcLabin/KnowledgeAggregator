# v1.0 Knowledge Aggregator

This tool is designed to be set up and used by a Large Language Model (LLM) assistant like the one in Cursor. Point your LLM to this README file and instruct it to follow the setup steps.

## What it does

Knowledge Aggregator is a Python script that collects information from various sources and consolidates it into a structured knowledge base. The included data sources are a starting template, and you can extend the script to support others.

**Supported by default:**
- Trello boards
- Google Sheets
- Supabase databases
- Local Git repositories

The output is a set of files that can be easily consumed by an LLM to understand the context of a project.

## ❗❗❗❗❗❗ For the Human User

Tell your LLM assistant what you want to achieve. For example:
- "Set up the Knowledge Aggregator for my new startup."
- "Create a new profile for my project 'Alpha' that pulls data from our Trello board and two Git repositories."
- "I need to add support for pulling data from a Notion database. Please modify the script."

Your LLM will handle the technical setup and modifications for you.

## ❗❗❗❗❗❗ LLM Assistant: Instructions

Follow these steps to set up and manage the project environment.

### 1. Initial Setup (First-Time Use)

1.  **Install Dependencies**: You'll need Node.js (for `npx`), the PostgreSQL client (`pg_dump`), and Python. Once those are ready, install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Create `.env` file**: Copy `env.example` to `.env`. This file will hold the API keys for the services the user wants to connect to. Leave unused keys blank.

### 2. Handling a User Request

When a user asks you to create a profile or add a data source, follow this logic:

1.  **Ask the User**: "What data sources do you want to aggregate for this project?"
2.  **Check Profile**: Does a profile for this project already exist in `projectsSources/`?
    - If **yes**, open it to see which sources are configured.
    - If **no**, create a new JSON profile file (e.g., `projectsSources/new_project.json`).
3.  **Configure Credentials & Profile**: For each requested data source:
    - **Is it supported?** (Check the list above).
      - If **yes**:
        - **Check `.env`**: Does the `.env` file have the necessary API keys (`TRELLO_API_KEY`, `GOOGLE_CLIENT_SECRETS_JSON`, etc.)? If not, guide the user on how to get them and add them to the file.
        - **Update Profile**: Add or update the configuration block for that source in the user's JSON profile.
      - If **no**:
        - **Inform User**: "This script doesn't currently support [New Data Source]. I will now modify the script to add this functionality."
        - **Modify Script**: Edit `knowledge_aggregator.py` to add the new functions required to fetch data from the new source.
        - **Update this README**: Add the new source to the "Supported by default" list.
        - **Proceed** with the configuration as if it were a supported source.

### Example Profile (`projectsSources/my_startup.json`)

A profile only needs to contain the sections for the data sources it actually uses.

```json
{
  "name": "My Awesome Startup",
  "output_dir": "knowledge_base_output/My_Awesome_Startup",
  "trello": {
    "boards": [
      {"id": "your_trello_board_id"}
    ]
  },
  "repositories": [
    {"path": "C:/path/to/your/local/repo"}
  ]
}
```

### Credentials Setup (As Needed)

-   **For Trello**:
    1.  Add `TRELLO_API_KEY` and `TRELLO_TOKEN` to the `.env` file.

-   **For Google Sheets**:
    1.  Go to the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
    2.  Create an **OAuth 2.0 Client ID** for a **Desktop app**.
    3.  Download the client secrets JSON, place it in the `auth/` directory.
    4.  Update `GOOGLE_CLIENT_SECRETS_JSON` in your `.env` file to point to this file (e.g., `auth/your_credentials_file.json`).

## How to Run

To run the aggregator, specify a profile using the `--profile` argument:

```bash
python knowledge_aggregator.py --profile projectsSources/my_startup.json
```

### Tip: Create a Wrapper Script

For convenience, create a wrapper script (e.g., `run_my_startup.bat`) inside the `WRAPPERS/` directory to run a profile's aggregation with one click. This directory is ignored by Git, so your personal scripts won't be committed.

**Example (`WRAPPERS/run_my_startup.bat` on Windows):**
```bat
@echo off
python ../knowledge_aggregator.py --profile ../projectsSources/my_startup.json
pause
```

## Security Notes

- The `.gitignore` file is configured to exclude sensitive files like `.env`, the `auth/` directory, `projectsSources/` and `WRAPPERS/`. **Do not commit them.**
- Keep personal API keys in your local `.env` file. Project-specific details are stored in the JSON profiles.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details. 