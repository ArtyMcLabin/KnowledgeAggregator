# v1.2 Knowledge Aggregator

This tool is designed to be set up and used by a Large Language Model (LLM) assistant like the one in Cursor. Point your LLM to this README file and instruct it to follow the setup steps.

## What it does

Knowledge Aggregator is a Python script that collects information from various sources and consolidates it into a structured knowledge base. The included data sources are a starting template, and you can extend the script to support others.

**Supported by default:**
- Trello boards
- Google Sheets
- Supabase databases (schema dump)
- Local Git repositories
- GitHub repositories (cloning, issues, and pull requests)

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

A profile's `sources` object only needs to contain keys for the data sources it actually uses.

```json
{
  "name": "My Awesome Startup",
  "output_dir": "knowledge_base_output/My_Awesome_Startup",
  "sources": {
    "trello_boards": [
      { "id": "your_trello_board_id" }
    ],
    "local_repositories": [
      { "path": "C:/path/to/your/local/repo" }
    ],
    "github_repositories": [
      {
        "url": "https://github.com/owner/repo-name",
        "fetch_issues": true,
        "fetch_prs": true
      }
    ],
  "google_sheets": [
      { "id": "your_google_sheet_id" }
  ],
    "supabase": {}
  }
}
```

### Credentials Setup (As Needed)

-   **For Trello**:
    1.  Add `TRELLO_API_KEY` and `TRELLO_TOKEN` to the `.env` file.

-   **For GitHub**:
    1.  Create a [Personal Access Token (Classic)](https://github.com/settings/tokens) with the `repo` scope.
    2.  Add it to your `.env` file as `GH_TOKEN`.

-   **For Google Sheets**:
    1.  Go to the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
    2.  Create an **OAuth 2.0 Client ID** for a **Desktop app**.
    3.  Download the client secrets JSON, place it in the `auth/` directory.
    4.  Update `GOOGLE_CLIENT_SECRETS_JSON` in your `.env` file to point to this file (e.g., `auth/your_credentials_file.json`).

-   **For Supabase**:
    1.  Navigate to your Supabase project's **Settings > API** and copy your `URL`. Add it to `.env` as `SUPABASE_URL`.
    2.  From the same page, copy the `service_role` key. Add it to `.env` as `SUPABASE_SERVICE_KEY`.
    3.  Navigate to **Settings > Database** and copy the `Connection string` URI. Add it to `.env` as `DB_URL`.

## How to Run

To run the aggregator, specify a profile using the `--profile` argument:

        ```bash
python knowledge_aggregator.py --profile projectsSources/my_startup.json
```

### Tip: Create a Python Wrapper Script

For convenience, create a Python wrapper script (e.g., `run_my_startup.py`) inside the `WRAPPERS/` directory to run a profile's aggregation with one click. This method is more reliable than batch files and ensures the console window stays open to display errors. This directory is ignored by Git, so your personal scripts won't be committed.

**Template for `run_my_startup.py`:**
```python
# v1.0
import subprocess
import sys
import os

def main():
    """
    Wrapper script to run the knowledge aggregator for a specific profile
    and keep the console window open after execution.
    """
    try:
        # --- !! IMPORTANT: SET YOUR PROFILE NAME HERE !! ---
        PROFILE_NAME = "my_startup.json"
        # ----------------------------------------------------

        # Get the directory of the current script to build the correct path to the main script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(script_dir, '..'))
        aggregator_script_path = os.path.join(project_root, 'knowledge_aggregator.py')
        profile_path = os.path.join(project_root, 'projectsSources', PROFILE_NAME)

        # Check if the main script and profile exist
        if not os.path.exists(aggregator_script_path):
            print(f"ERROR: Main script not found at {aggregator_script_path}")
            return
        if not os.path.exists(profile_path):
            print(f"ERROR: Profile '{PROFILE_NAME}' not found at {profile_path}")
            return

        # Build the command
        command = [
            sys.executable,  # Use the same python interpreter that is running this script
            aggregator_script_path,
            '--profile',
            profile_path
        ]

        print("="*50)
        print(f"Running Knowledge Aggregator for profile: {PROFILE_NAME}")
        print(f"Project Root: {project_root}")
        print("="*50)
        
        # Execute the command
        subprocess.run(command, check=True, cwd=project_root)

        print("\\n" + "="*50)
        print("Script finished successfully.")
        print("="*50)

    except subprocess.CalledProcessError as e:
        print("\\n" + "="*50)
        print(f"ERROR: The script failed with exit code {e.returncode}.")
        print("="*50)
    except Exception as e:
        print("\\n" + "="*50)
        print(f"An unexpected error occurred: {e}")
        print("="*50)
    finally:
        print("\\nPress Enter to exit...")
        input()

if __name__ == "__main__":
    main()
```

### ❗❗❗❗❗❗ Controlling `repomix` Output Size

The single most effective way to control the output size is to add a `.repomixignore` file to the root of your target repository (the one you are analyzing). Our script will automatically detect this file, read the patterns from it, and manually delete the specified folders before running the analysis.

This is the recommended approach. It keeps project-specific rules within the project itself.

**How to do it:**
1.  Create a file named `.repomixignore` in the root of the project you want to analyze (e.g., in your `my-awesome-project` repository).
2.  Add the paths to files and directories you want to exclude, one per line. Use the same syntax as a `.gitignore` file.
3.  I have created a ` ` file in this project with recommended defaults for a a generic web project site. You can use it as a starting point.

**Example `.repomixignore` for a a generic web project Project:**
```
# a generic web project core and plugin directories
node_modules/
dist/
build/


# Large vendor libraries


# Common log and package files
*.log

```

## Security Notes

- The `.gitignore`