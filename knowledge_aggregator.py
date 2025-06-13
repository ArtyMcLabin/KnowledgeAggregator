import os
import json
import configparser
import subprocess
import argparse
import sys
from datetime import datetime

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
import tempfile
import shutil
from github import Github, GithubException

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
        if fallback is None:
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
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Ensure auth directory exists
        os.makedirs('auth', exist_ok=True)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    return creds

# --- CORE FUNCTIONS ---

def fetch_trello_data(board_id, output_dir):
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
        
        output_path = os.path.join(output_dir, f"trello_board_{board_id}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(response.json(), f, ensure_ascii=False, indent=4)
        print_success(f"Trello data saved to {output_path}")

    except requests.exceptions.RequestException as e:
        print_error(f"Failed to fetch Trello data: {e}")

def list_directory_structure(repo_path, output_dir):
    """Creates a simple directory listing as a fallback when repomix fails."""
    repo_name = os.path.basename(os.path.normpath(repo_path))
    print_status(f"Creating directory listing for repository: {repo_name} (repomix fallback)...")
    
    if not os.path.isdir(repo_path):
        print_error(f"Repository path not found: {repo_path}")
        return False
    
    output_filename = os.path.join(output_dir, f"repo_{repo_name}_directory_listing.txt")
    
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

def process_repository_with_repomix(repo_path, output_dir):
    """Processes a repository using the repomix CLI tool."""
    repo_name = os.path.basename(os.path.normpath(repo_path))
    print_status(f"Processing repository with repomix: {repo_name}...")

    if not os.path.isdir(repo_path):
        print_error(f"Repository path not found: {repo_path}")
        return False  # Return False to indicate failure

    output_filename = os.path.join(output_dir, f"repo_{repo_name}_repomix.txt")
    
    command = [
        'npx', 'repomix',
        '--style', 'plain',
        '-o', output_filename,
        repo_path
    ]
    
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', shell=True)
        print_success(f"Repository '{repo_name}' processed by repomix into {output_filename}")
        if result.stdout:
            print_status(f"Repomix output:\n{result.stdout}")
        return True  # Return True to indicate success
    except FileNotFoundError:
        print_error(f"`npx` command not found. Is Node.js installed and in your PATH?")
        print_status(f"Falling back to directory listing for repository: {repo_name}")
        return list_directory_structure(repo_path, output_dir)
    except subprocess.CalledProcessError as e:
        print_error(f"Repomix failed for '{repo_name}' with exit code {e.returncode}:\n{e.stderr}")
        print_status(f"Falling back to directory listing for repository: {repo_name}")
        success = list_directory_structure(repo_path, output_dir)
        if not success:
            print_error(f"Fallback directory listing also failed for '{repo_name}'")
        return success

def fetch_google_sheet(sheet_id, creds, output_dir):
    """Exports a Google Sheet to a CSV file."""
    print_status(f"Fetching Google Sheet: {sheet_id}...")
    
    try:
        service = build('drive', 'v3', credentials=creds)
        request = service.files().export_media(fileId=sheet_id, mimeType='text/csv')
        
        output_path = os.path.join(output_dir, f"google_sheet_{sheet_id}.csv")
        fh = io.FileIO(output_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print_status(f"Downloading Google Sheet: {int(status.progress() * 100)}% complete.")
            
        print_success(f"Google Sheet exported to {output_path}")

    except HttpError as e:
        print_error(f"An error occurred with Google API for sheet {sheet_id}: {e}. Check Sheet ID and sharing settings.")

def fetch_github_issues(repo_name, output_dir):
    """Fetches a GitHub repository's issues using the gh CLI."""
    print_status(f"Fetching GitHub issues for {repo_name}...")
    output_filename = os.path.join(output_dir, f"repo_{repo_name.replace('/', '_')}_issues.json")
    command = [
        'gh', 'issue', 'list',
        '-R', repo_name,
        '--json', 'title,body,state,createdAt,updatedAt,author,comments,labels,number,url',
        '--limit', '500' # Adjust limit as needed
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', shell=True)
        issues = json.loads(result.stdout)
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(issues, f, ensure_ascii=False, indent=4)
        print_success(f"GitHub issues for '{repo_name}' saved to {output_filename}")
        return True
    except FileNotFoundError:
        print_error("`gh` command not found. Please install the GitHub CLI: https://cli.github.com/")
        return False
    except subprocess.CalledProcessError as e:
        print_error(f"GitHub CLI failed while fetching issues for '{repo_name}':\n{e.stderr}")
        return False
    except json.JSONDecodeError:
        print_error(f"Failed to parse JSON from GitHub CLI output for issues of '{repo_name}'.")
        return False

def fetch_github_prs(repo_name, output_dir):
    """Fetches a GitHub repository's pull requests using the gh CLI."""
    print_status(f"Fetching GitHub PRs for {repo_name}...")
    output_filename = os.path.join(output_dir, f"repo_{repo_name.replace('/', '_')}_prs.json")
    command = [
        'gh', 'pr', 'list',
        '-R', repo_name,
        '--json', 'title,body,state,createdAt,updatedAt,author,comments,labels,number,url,reviews',
        '--limit', '500' # Adjust limit as needed
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', shell=True)
        prs = json.loads(result.stdout)
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(prs, f, ensure_ascii=False, indent=4)
        print_success(f"GitHub PRs for '{repo_name}' saved to {output_filename}")
        return True
    except FileNotFoundError:
        print_error("`gh` command not found. Please install the GitHub CLI: https://cli.github.com/")
        return False
    except subprocess.CalledProcessError as e:
        print_error(f"GitHub CLI failed while fetching PRs for '{repo_name}':\n{e.stderr}")
        return False
    except json.JSONDecodeError:
        print_error(f"Failed to parse JSON from GitHub CLI output for PRs of '{repo_name}'.")
        return False

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
        print_error(f"GitHub CLI failed while cloning '{repo_url}':\n{e.stderr}")
        return False

def dump_supabase_schema(db_config, output_dir):
    """Extracts the Supabase database schema using the Supabase REST API."""
    print_status("Extracting Supabase DB schema...")
    
    try:
        # Extract required fields from the config
        api_url = db_config.get('api_url')
        service_role_key = db_config.get('service_role_key')
        
        if not api_url or not service_role_key:
            print_error("Supabase API URL or service role key not provided in the project profile.")
        
        # Create a Supabase client
        supabase: Client = create_client(api_url, service_role_key)
        
        # Output file path
        output_path = os.path.join(output_dir, f"supabase_schema_{api_url.replace('https://', '').replace('.', '_')}.json")
        
        # Dictionary to store schema information
        schema_data = {
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "api_url": api_url
            },
            "schemas": {},
            "tables": {},
            "functions": {},
            "extensions": []
        }
        
        # Fetch database schema information using RPC
        try:
            # Get all tables
            response = supabase.table("pg_tables").select("*").execute()
            tables_data = response.data
            
            for table in tables_data:
                schema_name = table.get("schemaname")
                table_name = table.get("tablename")
                
                # Skip system schemas
                if schema_name in ['pg_catalog', 'information_schema', 'extensions', 
                                  'graphql', 'graphql_public', 'pgbouncer', 
                                  'realtime', 'storage']:
                    continue
                
                # Add schema if not already in our data
                if schema_name not in schema_data["schemas"]:
                    schema_data["schemas"][schema_name] = {
                        "name": schema_name,
                        "tables": []
                    }
                
                # Add table to schema's tables list
                if table_name not in schema_data["schemas"][schema_name]["tables"]:
                    schema_data["schemas"][schema_name]["tables"].append(table_name)
                
                # Get table columns
                table_key = f"{schema_name}.{table_name}"
                schema_data["tables"][table_key] = {
                    "name": table_name,
                    "schema": schema_name,
                    "columns": []
                }
                
                # Fetch columns for this table using RPC
                try:
                    # We'll use a direct REST API call since the Supabase Python client
                    # doesn't have built-in methods for schema introspection
                    headers = {
                        "apikey": service_role_key,
                        "Authorization": f"Bearer {service_role_key}",
                        "Content-Type": "application/json"
                    }
                    
                    # Call RPC to get columns
                    rpc_payload = {
                        "schema": schema_name,
                        "table": table_name
                    }
                    
                    rpc_url = f"{api_url}/rest/v1/rpc/get_columns"
                    columns_response = requests.post(
                        rpc_url,
                        headers=headers,
                        json=rpc_payload
                    )
                    
                    if columns_response.status_code == 200:
                        columns = columns_response.json()
                        schema_data["tables"][table_key]["columns"] = columns
                    else:
                        print_status(f"Could not fetch columns for {table_key}. Using fallback method.")
                        # Fallback: Just record the table name without column details
                        pass
                        
                except Exception as e:
                    print_status(f"Error fetching columns for {table_key}: {e}")
            
        except Exception as e:
            print_status(f"Error fetching tables: {e}")
        
        # Write the schema data to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(schema_data, f, indent=2)
        
        print_success(f"Supabase schema information saved to {output_path}")
        
    except Exception as e:
        print_error(f"Failed to extract Supabase schema: {e}")

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
    args = parser.parse_args()

    # Load the specified profile
    profile = load_profile(args.profile)
    project_name = profile.get('name', 'default_project')
    output_dir = profile.get('output_dir', os.path.join('knowledge_base_output', project_name))

    # --- SCRIPT EXECUTION ---
    start_time = datetime.now()
    print_status(f"Starting knowledge aggregation for project '{project_name}' at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Process all data sources
    sources = profile.get("data_sources", {})
    
    google_creds = None
    if "google_sheets" in sources:
        print_status("Authenticating with Google...")
        google_creds = get_google_creds()
        print_success("Google authentication successful.")

    for trello_board in sources.get("trello", []):
        fetch_trello_data(trello_board["board_id"], output_dir)

    if 'google_sheets' in profile:
        for sheet in profile['google_sheets']:
            fetch_google_sheet(sheet['id'], google_creds, output_dir)
    
    if 'supabase' in profile:
        dump_supabase_schema(profile['supabase'], output_dir)

    # Process local repositories
    if 'repositories' in profile:
        for repo in profile['repositories']:
            process_repository_with_repomix(repo['path'], output_dir)
    
    # Process GitHub repositories
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

            # Create a dedicated temp folder for the clone
            temp_base_path = os.path.join('temp', repo_name.replace('/', '_'))
            
            try:
                # 1. Clone repo and process with repomix
                if clone_github_repo(repo_url, temp_base_path):
                    process_repository_with_repomix(temp_base_path, output_dir)

                # 2. Fetch issues if requested
                if repo_info.get('fetch_issues'):
                    fetch_github_issues(repo_name, output_dir)
                
                # 3. Fetch PRs if requested
                if repo_info.get('fetch_prs'):
                    fetch_github_prs(repo_name, output_dir)
            finally:
                # Ensure the temporary directory is always removed
                if os.path.isdir(temp_base_path):
                    print_status(f"Cleaning up temporary directory: {temp_base_path}")
                    shutil.rmtree(temp_base_path)

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


if __name__ == '__main__':
    main()