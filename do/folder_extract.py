import os
import re
import json
import random
from datetime import datetime
import boto3
from dotenv import load_dotenv

load_dotenv()

access_key = os.getenv('DO_SPACES_KEY')
secret_key = os.getenv('DO_SPACES_SECRET')
region = os.getenv('DO_SPACES_REGION')
endpoint = os.getenv('DO_SPACES_ENDPOINT')
bucket_name = os.getenv('DO_SPACES_BUCKET')

TARGET_FOLDERS = ["inimigos-da-claridade", "нұнөбек зиманбаев", "vendee-rouge", "solastalgia", "nuri-mazin"]


def download_files_from_do_spaces(target_folders=None):
    try:
        session = boto3.session.Session()
        client = session.client(
            's3',
            region_name=region,
            endpoint_url=f"https://{endpoint}",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )

        response = client.list_objects_v2(Bucket=bucket_name)
        files = []

        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                if not key.endswith('/'):
                    files.append(key)

            print(f"Found {len(files)} files")

            if target_folders:
                selected_files = []

                for target_folder in target_folders:
                    target_files = [f for f in files if target_folder in f and not f.endswith('/')]

                    if target_files:
                        folder_selection = random.sample(target_files, min(10, len(target_files)))
                        selected_files.extend(folder_selection)

                if selected_files:
                    os.makedirs("music", exist_ok=True)

                    for file_path in selected_files:
                        artist_name = None
                        for folder in target_folders:
                            if folder in file_path:
                                artist_name = folder
                                break

                        if artist_name:
                            artist_folder = os.path.join("music", artist_name)
                            os.makedirs(artist_folder, exist_ok=True)

                            try:
                                response = client.head_object(Bucket=bucket_name, Key=file_path)
                                content_type = response.get('ContentType', '')

                                if 'audio/mpeg' in content_type or 'mp3' in content_type:
                                    extension = '.mp3'
                                elif 'audio/wav' in content_type or 'wav' in content_type:
                                    extension = '.wav'
                                else:
                                    extension = '.mp3'

                                filename = os.path.basename(file_path) + extension
                                local_path = os.path.join(artist_folder, filename)

                                if os.path.exists(local_path):
                                    print(f"Skipped (exists): {local_path}")
                                    continue

                                client.download_file(bucket_name, file_path, local_path)
                                print(f"Downloaded: {local_path}")

                            except Exception as e:
                                print(f"Failed to download {file_path}: {e}")

                    return len(selected_files)
                else:
                    return 0
            else:
                return 0
        else:
            return 0
    except Exception as e:
        print(f"Failed: {e}")
        return 0


if __name__ == "__main__":
    downloaded = download_files_from_do_spaces(TARGET_FOLDERS)
    print(f"Downloaded {downloaded} files")