# v1.4 - Added repomix --compress and --remote support
import os
import json
import configparser
import subprocess
import argparse
import sys
from datetime import datetime
import tempfile
import shutil
from github import Github, GithubException
import stat

# Third-party libraries - install via requirements.txt
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import io
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
from supabase import create_client, Client

# --- CONFIGURATION & CONSTANTS ---

# Load environment variables from .env file
load_dotenv()

# Patterns to ignore when collapsing repositories. Add any other files/dirs you want to skip.
# Uses .gitignore-style matching.
REPO_IGNORE_PATTERNS = [
    ".git/",
    ".vscode/",
    "__pycache__/",
    "node_modules/",
    "dist/",
    "build/",
    "vendor/",
    "*.pyc",
    "*.log",
    "*.swp",
    "*.DS_Store",
    ".env"
]

# --- HELPER FUNCTIONS ---

def print_status(message):
    """Prints a status message to the console."""
    print(f"[INFO] {message}")

def print_success(message):
    """Prints a success message to the console."""
    print(f"[SUCCESS] {message}")

def print_error(message):
    """Prints an error message and exits the script."""
    print(f"[ERROR] {message}", file=sys.stderr)
    sys.exit(1)

def should_ignore(path, ignore_patterns):
    """Checks if a file path matches any of the ignore patterns."""
    import fnmatch
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(path, pattern) or any(fnmatch.fnmatch(part, pattern.strip('/')) for part in path.split(os.sep)):
            return True
    return False

def get_env_var(var_name, fallback=None):
    """Gets an environment variable or returns a fallback value."""
    value = os.environ.get(var_name)
    if value is None:
        # If fallback is explicitly provided (even if it's None), return it.
        # Only error out if no fallback was specified at all.
        if fallback is None and var_name not in ['GH_TOKEN']: # Allow GH_TOKEN to be absent
            print_error(f"Required environment variable '{var_name}' is not set.")
        return fallback
    return value

# --- GOOGLE OAUTH FLOW ---

def get_google_creds():
    """Handles Google OAuth2 flow and returns credentials."""
    creds = None
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    token_path = os.path.join('auth', 'token.json')
    creds_path = get_env_var('GOOGLE_CLIENT_SECRETS_JSON')

    if not os.path.exists(creds_path):
        print_error(f"Google client secrets file not found at the path specified in GOOGLE_CLIENT_SECRETS_JSON: {creds_path}. Please check your .env file.")

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print_status("Attempting to refresh expired Google token...")
                creds.refresh(Request())
                print_success("Google token refreshed successfully")
            except Exception as e:
                print_status(f"Token refresh failed: {str(e)}")
                print_status("Starting new OAuth flow...")
                creds = None  # Force new OAuth flow
        
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Ensure auth directory exists
        os.makedirs('auth', exist_ok=True)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    return creds

# --- CORE FUNCTIONS ---

def fetch_trello_data(board_id, output_dir, date_prefix):
    """Fetches a Trello board's data as JSON."""
    print_status(f"Fetching Trello data for board: {board_id}...")
    api_key = get_env_var('TRELLO_API_KEY')
    token = get_env_var('TRELLO_TOKEN')

    url = f"https://api.trello.com/1/boards/{board_id}"
    params = {
        'key': api_key,
        'token': token,
        'fields': 'name,desc,url',
        'lists': 'open',
        'cards': 'all',
        'card_fields': 'name,desc,due,labels,url,shortUrl',
        'labels': 'all'
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        output_path = os.path.join(output_dir, f"{date_prefix}_trello_board_{board_id}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(response.json(), f, ensure_ascii=False, indent=4)
        print_success(f"Trello data saved to {output_path}")

    except requests.exceptions.RequestException as e:
        print_error(f"Failed to fetch Trello data: {e}")

def list_directory_structure(repo_path, output_dir, date_prefix):
    """Creates a simple directory listing as a fallback when repomix fails."""
    repo_name = os.path.basename(os.path.normpath(repo_path))
    print_status(f"Creating directory listing for repository: {repo_name} (repomix fallback)...")
    
    if not os.path.isdir(repo_path):
        print_error(f"Repository path not found: {repo_path}")
        return False
    
    output_filename = os.path.join(output_dir, f"{date_prefix}_repo_{repo_name}_directory_listing.txt")
    
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(f"# Directory Structure for {repo_name}\n\n")
            
            # List top-level files and directories
            f.write("## Root\n\n")
            for item in sorted(os.listdir(repo_path)):
                item_path = os.path.join(repo_path, item)
                if os.path.isdir(item_path):
                    f.write(f"- Directory: {item}\n")
                else:
                    f.write(f"- File: {item}\n")
            
            # For each top-level directory, list its contents
            for item in sorted(os.listdir(repo_path)):
                item_path = os.path.join(repo_path, item)
                if os.path.isdir(item_path) and not should_ignore(item, REPO_IGNORE_PATTERNS):
                    f.write(f"\n## {item}\n\n")
                    try:
                        for subitem in sorted(os.listdir(item_path)):
                            if not should_ignore(os.path.join(item, subitem), REPO_IGNORE_PATTERNS):
                                f.write(f"- {subitem}\n")
                    except Exception as e:
                        f.write(f"Error listing directory: {str(e)}\n")
        
        print_success(f"Directory listing saved to {output_filename}")
        return True
    except Exception as e:
        print_error(f"Failed to create directory listing: {str(e)}")
        
        # Last resort: create a minimal file
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(f"# Repository {repo_name} could not be processed\n")
                f.write(f"Error: {str(e)}\n")
            print_success(f"Minimal fallback file created at {output_filename}")
            return True
        except Exception as e2:
            print_error(f"Even minimal fallback failed: {str(e2)}")
            return False

def remove_readonly(func, path, _):
    """Clear the readonly bit and re-attempt the removal"""
    os.chmod(path, stat.S_IWRITE)
    func(path)

def process_repository_with_repomix(repo_path_or_url, output_dir, date_prefix, compress=False, remote=False, ignore_patterns=None):
    """Processes a repository using the repomix CLI tool with optional compression and remote support."""
    if remote:
        # For remote repositories, extract repo name from URL
        repo_name = repo_path_or_url.split('/')[-1].replace('.git', '')
        if '/' in repo_path_or_url.split('/')[-2:][0]:
            repo_name = '_'.join(repo_path_or_url.split('/')[-2:]).replace('.git', '')
        print_status(f"Processing remote repository with repomix: {repo_path_or_url}...")
    else:
        # For local repositories
        repo_name = os.path.basename(os.path.normpath(repo_path_or_url))
        print_status(f"Processing local repository with repomix: {repo_name}...")
        
        if not os.path.isdir(repo_path_or_url):
            print_error(f"Repository path not found: {repo_path_or_url}")
            return False

    # repomix --compress doesn't create a .gz file, it just makes the text output smaller.
    output_filename = os.path.join(output_dir, f"{date_prefix}_repo_{repo_name}_repomix.txt")
    
    # --- Build repomix command ---
    command = [
        'npx', 'repomix',
        '--style', 'plain',
        '-o', output_filename
    ]
    
    # Add compression flag if requested
    if compress:
        command.append('--compress')
        print_status("Compression enabled for repomix output")
    
    # Add remote flag if processing remote repository
    if remote:
        command.append('--remote')
        command.append(repo_path_or_url)
        print_status(f"Using repomix --remote for {repo_path_or_url}")
    else:
        # For local repositories, handle ignore patterns
        if ignore_patterns:
            print_status(f"Applying {len(ignore_patterns)} custom ignore patterns")
            for pattern in ignore_patterns:
                if pattern.strip() and not pattern.strip().startswith('#'):
                    command.extend(['--ignore', pattern.strip()])
        else:
            # Prioritize .repomixignore from the target repo, but fall back to local one
            ignore_file_path = os.path.join(repo_path_or_url, '.repomixignore')
            if not os.path.exists(ignore_file_path):
                print_status("No .repomixignore found in target repo, using local fallback.")
                ignore_file_path = '.repomixignore' # Use local file

            if os.path.exists(ignore_file_path):
                print_status(f"Applying ignore patterns from {os.path.abspath(ignore_file_path)}.")
                with open(ignore_file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        pattern = line.strip()
                        if pattern and not pattern.startswith('#'):
                            command.extend(['--ignore', pattern])
        
        command.append(repo_path_or_url)
    
    try:
        # Re-adding shell=True as it's needed for npx.cmd on Windows.
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', shell=True)
        
        # Check if output file was created and get its size
        if os.path.exists(output_filename):
            file_size = os.path.getsize(output_filename)
            size_mb = file_size / (1024 * 1024)
            print_success(f"Repository '{repo_name}' processed by repomix into {output_filename} ({size_mb:.2f} MB)")
        else:
            print_success(f"Repository '{repo_name}' processed by repomix into {output_filename}")
            
        if result.stdout:
            print_status("Repomix output:")
            # Print stdout directly to preserve formatting without adding extra newlines
            print(result.stdout.strip())
        return True
        
    except FileNotFoundError:
        print_error(f"`npx` command not found. Is Node.js installed and in your PATH?")
        if not remote:  # Only fallback for local repos
            print_status(f"Falling back to directory listing for repository: {repo_name}")
            return list_directory_structure(repo_path_or_url, output_dir, date_prefix)
        return False
        
    except subprocess.CalledProcessError as e:
        error_message = f"Repomix failed for '{repo_name}' with exit code {e.returncode}."
        # Ensure stderr is captured and decoded correctly
        stderr_output = e.stderr.strip() if e.stderr else "No stderr output."
        print_error(f"{error_message}\n--- Start of Repomix Error ---\n{stderr_output}\n--- End of Repomix Error ---")

        if not remote:  # Only fallback for local repos
            print_status(f"Falling back to directory listing for repository: {repo_name}")
            success = list_directory_structure(repo_path_or_url, output_dir, date_prefix)
            if not success:
                print_error("Fallback directory listing also failed.")
        return False

def fetch_google_sheet(sheet_id, creds, output_dir, date_prefix):
    """Exports a Google Sheet to a CSV file."""
    print_status(f"Fetching Google Sheet: {sheet_id}...")
    
    try:
        service = build('drive', 'v3', credentials=creds)
        request = service.files().export_media(fileId=sheet_id, mimeType='text/csv')
        
        output_path = os.path.join(output_dir, f"{date_prefix}_google_sheet_{sheet_id}.csv")
        fh = io.FileIO(output_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f"Downloading Google Sheet: {int(status.progress() * 100)}% complete.")
            
        print_success(f"Google Sheet exported to {output_path}")

    except HttpError as e:
        print_error(f"An error occurred with Google API for sheet {sheet_id}: {e}. Check Sheet ID and sharing settings.")

def fetch_github_issues(repo_name, output_dir, date_prefix):
    """Fetches a GitHub repository's issues using the gh CLI."""
    print_status(f"Fetching GitHub issues for {repo_name}...")
    output_filename = os.path.join(output_dir, f"{date_prefix}_repo_{repo_name.replace('/', '_')}_issues.json")
    command = [
        'gh', 'issue', 'list',
        '-R', repo_name,
        '--json', 'title,body,state,createdAt,updatedAt,author,comments,labels,number,url',
        '--limit', '500' # Adjust limit as needed
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', shell=True)
        issues = json.loads(result.stdout)
        
        if not issues:
            print_status(f"No open issues found for {repo_name}. Skipping file creation.")
            return

        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(issues, f, ensure_ascii=False, indent=4)
        print_success(f"Successfully saved {len(issues)} issues for '{repo_name}' to {output_filename}")
    
    except FileNotFoundError:
        print_error("`gh` command not found. Please install the GitHub CLI: https://cli.github.com/")
    except subprocess.CalledProcessError as e:
        print_error(f"GitHub CLI failed while fetching issues for '{repo_name}':\n{e.stderr}")
    except json.JSONDecodeError:
        print_error(f"Failed to parse JSON from GitHub CLI output for issues of '{repo_name}'.")

def fetch_github_prs(repo_name, output_dir, date_prefix):
    """Fetches a GitHub repository's pull requests using the gh CLI."""
    print_status(f"Fetching GitHub pull requests for {repo_name}...")
    output_filename = os.path.join(output_dir, f"{date_prefix}_repo_{repo_name.replace('/', '_')}_pullRequests.json")
    command = [
        'gh', 'pr', 'list',
        '-R', repo_name,
        '--json', 'title,body,state,createdAt,updatedAt,author,comments,labels,number,url,reviews',
        '--limit', '500' # Adjust limit as needed
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', shell=True)
        prs = json.loads(result.stdout)

        if not prs:
            print_status(f"No open pull requests found for {repo_name}. Skipping file creation.")
            return

        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(prs, f, ensure_ascii=False, indent=4)
        print_success(f"Successfully saved {len(prs)} pull requests for '{repo_name}' to {output_filename}")

    except FileNotFoundError:
        print_error("`gh` command not found. Please install the GitHub CLI: https://cli.github.com/")
    except subprocess.CalledProcessError as e:
        print_error(f"GitHub CLI failed while fetching PRs for '{repo_name}':\n{e.stderr}")
    except json.JSONDecodeError:
        print_error(f"Failed to parse JSON from GitHub CLI output for PRs of '{repo_name}'.")

def clone_github_repo(repo_url, temp_dir):
    """Clones a GitHub repository into a temporary directory."""
    print_status(f"Cloning GitHub repository: {repo_url}...")
    command = ['gh', 'repo', 'clone', repo_url, temp_dir]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', shell=True)
        print_success(f"Successfully cloned {repo_url} to {temp_dir}")
        return True
    except FileNotFoundError:
        print_error("`gh` command not found. Please install the GitHub CLI: https://cli.github.com/")
        return False
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to clone repository '{repo_url}': {e.stderr}")
        return False

def dump_postgres_schema(database_url, output_dir, date_prefix):
    """Extracts a PostgreSQL database schema using a direct connection."""
    print_status("Extracting PostgreSQL DB schema...")
    
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        db_name = conn.get_dsn_parameters().get('dbname', 'postgres')
        output_path = os.path.join(output_dir, f"{date_prefix}_postgres_schema_{db_name}.json")

        schema_data = {
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "db_name": db_name
            },
            "schemas": {},
            "tables": {}
        }

        # Get all schemas and the tables within them
        cur.execute("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
              AND schema_name NOT LIKE 'pg_temp_%' AND schema_name NOT LIKE 'pg_toast_temp_%';
        """)
        schemas = cur.fetchall()

        for schema in schemas:
            schema_name = schema['schema_name']
            schema_data["schemas"][schema_name] = {"name": schema_name, "tables": []}

            # Get all tables for the current schema
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s;
            """, (schema_name,))
            tables = cur.fetchall()

            for table in tables:
                table_name = table['table_name']
                table_key = f"{schema_name}.{table_name}"
                schema_data["schemas"][schema_name]["tables"].append(table_name)
                
                # Get all columns for the current table
                cur.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position;
                """, (schema_name, table_name))
                columns = cur.fetchall()
                
                schema_data["tables"][table_key] = {
                    "name": table_name,
                    "schema": schema_name,
                    "columns": [dict(col) for col in columns]
                }
        
        cur.close()
        conn.close()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(schema_data, f, indent=2, default=str) # Use default=str to handle complex data types
        
        print_success(f"PostgreSQL schema saved to {output_path}")

    except psycopg2.Error as e:
        print_error(f"Database connection or query failed: {e}")
    except Exception as e:
        print_error(f"An unexpected error occurred during PostgreSQL schema dump: {e}")

def load_profile(profile_path):
    """Loads a JSON profile file."""
    if not profile_path:
        print_error("No profile specified. Use the --profile argument to provide the path to a JSON profile file.")
    try:
        with open(profile_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print_error(f"Profile file not found: {profile_path}")
    except json.JSONDecodeError:
        print_error(f"Invalid JSON in profile file: {profile_path}")

# --- MAIN EXECUTION ---

def main():
    """Main function to run the knowledge aggregator."""
    parser = argparse.ArgumentParser(description="Knowledge Aggregator for LLMs")
    parser.add_argument('--profile', type=str, required=True, help='Path to the project profile JSON file.')
    parser.add_argument('--no-pause', action='store_true', help='Do not pause for user input at the end of the script.')
    args = parser.parse_args()

    # Load the specified profile
    profile = load_profile(args.profile)
    project_name = profile.get('name', 'default_project')
    output_dir = profile.get('output_dir', os.path.join('knowledge_base_output', project_name))

    # --- SCRIPT EXECUTION ---
    start_time = datetime.now()
    date_prefix = start_time.strftime('%d_%m_%Y')
    print_status(f"Starting knowledge aggregation for project '{project_name}' at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Clean and create output directory
    if os.path.exists(output_dir):
        print_status(f"Output directory '{output_dir}' exists. Cleaning it before run...")
        for filename in os.listdir(output_dir):
            file_path = os.path.join(output_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print_error(f'Failed to delete {file_path}. Reason: {e}')
    else:
        os.makedirs(output_dir)

    # --- Process all data sources from top-level keys (reverted logic) ---
    google_creds = None
    if 'google_sheets' in profile:
        print_status("Authenticating with Google...")
        google_creds = get_google_creds()
        print_success("Google authentication successful.")

    if 'trello' in profile and 'boards' in profile['trello']:
        for trello_board in profile['trello']['boards']:
            fetch_trello_data(trello_board.get("id"), output_dir, date_prefix)

    if 'google_sheets' in profile:
        for sheet in profile['google_sheets']:
            fetch_google_sheet(sheet.get("id"), google_creds, output_dir, date_prefix)
    
    # --- Database Processing ---
    # Prioritize standard PostgreSQL connection if available
    if 'database_url' in profile:
        dump_postgres_schema(profile['database_url'], output_dir, date_prefix)

    # Process local repositories
    if 'repositories' in profile:
        for repo in profile['repositories']:
            # Extract compression and ignore patterns from repo config
            compress = repo.get('compress', False)
            ignore_patterns = repo.get('ignore_patterns', None)
            process_repository_with_repomix(
                repo.get('path'), 
                output_dir, 
                date_prefix, 
                compress=compress, 
                remote=False, 
                ignore_patterns=ignore_patterns
            )
    
    # Process GitHub repositories using repomix --remote
    if 'github_repositories' in profile:
        for repo_info in profile['github_repositories']:
            repo_url = repo_info.get('url')
            if not repo_url:
                continue

            # Extract owner/repo from URL for API calls
            try:
                repo_name = '/'.join(repo_url.split('/')[-2:]).replace('.git', '')
            except IndexError:
                print_error(f"Could not parse repository name from URL: {repo_url}")
                continue

            # Extract compression and ignore patterns from repo config
            compress = repo_info.get('compress', False)
            ignore_patterns = repo_info.get('ignore_patterns', None)
            
            # Use repomix --remote instead of manual cloning
            process_repository_with_repomix(
                repo_url, 
                output_dir, 
                date_prefix, 
                compress=compress, 
                remote=True, 
                ignore_patterns=ignore_patterns
            )

            # Fetch issues if requested
            if repo_info.get('fetch_issues'):
                fetch_github_issues(repo_name, output_dir, date_prefix)
            
            # Fetch PRs if requested
            if repo_info.get('fetch_prs'):
                fetch_github_prs(repo_name, output_dir, date_prefix)

    # --- FINAL MESSAGE ---
    end_time = datetime.now()
    duration = end_time - start_time
    print_success(f"All tasks for project '{project_name}' completed in {duration}.")
    
    # Open the output directory for the user
    try:
        print_success(f"Your consolidated knowledge base is ready. Opening output directory: {output_dir}")
        if sys.platform == "win32":
            os.startfile(os.path.realpath(output_dir))
        elif sys.platform == "darwin":
            subprocess.run(["open", os.path.realpath(output_dir)])
        else:
            subprocess.run(["xdg-open", os.path.realpath(output_dir)])
    except Exception as e:
        print_error(f"Could not open output directory '{output_dir}'. Please open it manually. Error: {e}")

    # Final pause unless disabled
    if not args.no_pause:
        print("\nPress Enter to exit...")
        input()


if __name__ == '__main__':
    main()