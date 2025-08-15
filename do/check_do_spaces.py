import os
import re
import json
import random
from datetime import datetime
import boto3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get environment variables for DigitalOcean Spaces
access_key = os.getenv('DO_SPACES_KEY')
secret_key = os.getenv('DO_SPACES_SECRET')
region = os.getenv('DO_SPACES_REGION')
endpoint = os.getenv('DO_SPACES_ENDPOINT')
bucket_name = os.getenv('DO_SPACES_BUCKET')


def get_files_from_do_spaces():
    try:
        session = boto3.session.Session()
        client = session.client(
            's3',
            region_name=region,
            endpoint_url=f"https://{endpoint}",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )

        # Get all objects in the bucket
        response = client.list_objects_v2(Bucket=bucket_name)

        files = []
        folders = set()

        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                # Check if it's a folder
                if key.endswith('/'):
                    folders.add(key)
                # Otherwise it's a file
                else:
                    files.append(key)

                    # Add parent folders
                    parts = key.split('/')
                    if len(parts) > 1:
                        for i in range(1, len(parts)):
                            folder = '/'.join(parts[:i]) + '/'
                            folders.add(folder)

            # Convert folders to list
            folders = list(folders)
            print(f"Found {len(files)} files and {len(folders)} folders")

            if folders:
                print("\nFolders:")
                for folder in folders[:10]:  # Show first 10 folders
                    print(f"- {folder}")
                if len(folders) > 10:
                    print(f"... and {len(folders) - 10} more")

            # If folders exist, randomly select files and folders
            if folders:
                # Decide whether to pick from specific folders
                use_folders = random.choice([True, False])

                if use_folders and folders:
                    print("\nSelecting from specific folders")
                    # Select random folders
                    selected_folders = random.sample(folders, min(3, len(folders)))
                    print("Selected folders:")
                    for folder in selected_folders:
                        print(f"- {folder}")

                    selected_files = []

                    # Get files from the selected folders
                    for folder in selected_folders:
                        folder_files = [f for f in files if f.startswith(folder)]
                        if folder_files:
                            folder_selection = random.sample(folder_files, min(5, len(folder_files)))
                            print(f"\nSelected {len(folder_selection)} files from folder '{folder}':")
                            for file in folder_selection:
                                print(f"- {file}")
                            selected_files.extend(folder_selection)

                    # If we didn't get enough files from folders, add some random ones
                    if len(selected_files) < 10 and files:
                        remaining_files = [f for f in files if f not in selected_files]
                        additional_count = min(10 - len(selected_files), len(remaining_files))
                        if additional_count > 0:
                            additional_files = random.sample(remaining_files, additional_count)
                            print(f"\nAdded {len(additional_files)} additional random files to reach minimum count:")
                            for file in additional_files:
                                print(f"- {file}")
                            selected_files.extend(additional_files)

                    print(f"\nTotal selected files: {len(selected_files)}")
                    return selected_files
                else:
                    print("\nSelecting random files from entire bucket")

            # Default: return random files from the entire bucket
            selected_files = random.sample(files, min(25, len(files)))
            print(f"\nSelected {len(selected_files)} random files from entire bucket")
            for file in selected_files[:10]:  # Show first 10 files
                print(f"- {file}")
            if len(selected_files) > 10:
                print(f"... and {len(selected_files) - 10} more")

            return selected_files
        else:
            print("No files found in the bucket.")
            return []
    except Exception as e:
        print(f"Failed to fetch files from DigitalOcean Spaces: {e}")
        return []


def test_file_selection():
    print("Testing file selection from DigitalOcean Spaces...")
    print(f"Bucket: {bucket_name}")
    print(f"Endpoint: {endpoint}")
    print("=" * 50)

    selected_files = get_files_from_do_spaces()

    print("=" * 50)
    print(f"Selection complete. Total files selected: {len(selected_files)}")


if __name__ == "__main__":
    test_file_selection()