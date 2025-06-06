import os
import boto3
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

ACCESS_KEY = os.getenv('DO_SPACES_KEY')
SECRET_KEY = os.getenv('DO_SPACES_SECRET')
REGION = os.getenv('DO_SPACES_REGION')
ENDPOINT_URL = os.getenv('DO_SPACES_ENDPOINT')
BUCKET_NAME = os.getenv('DO_SPACES_BUCKET')

TARGET_DO_FOLDER_PREFIX = "house/"
NEW_EXTENSION = ".mp3"
DRY_RUN = False


def check_if_object_exists(s3_client, bucket: str, key: str) -> bool:
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            print(f"      Error checking existence of {key}: {e}")
            raise


def rename_files_add_extension(
        s3_client,
        bucket: str,
        target_prefix: str,
        new_extension: str,
        dry_run: bool = True
):
    print(f"--- Starting file rename process ---")
    print(f"Bucket: {bucket}")
    print(f"Target Prefix: '{target_prefix}'")
    print(f"New Extension to add: '{new_extension}'")
    print(f"DRY RUN: {'ENABLED' if dry_run else 'DISABLED - ACTUAL RENAMING WILL OCCUR'}")
    if not dry_run:
        print(f"WARNING: DRY RUN IS DISABLED. This will attempt to rename files in '{bucket}/{target_prefix}'.")
    print("------------------------------------")

    renamed_count = 0
    skipped_already_correct_ext_count = 0
    skipped_has_other_ext_count = 0
    skipped_folders_count = 0
    conflict_count = 0
    error_count = 0

    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=bucket, Prefix=target_prefix)

        for page in page_iterator:
            if "Contents" not in page:
                continue

            for obj in page['Contents']:
                original_key = obj['Key']
                print(f"\nProcessing: {original_key}")

                if original_key.endswith('/'):
                    print(f"  Skipping (is a folder marker): {original_key}")
                    skipped_folders_count += 1
                    continue

                if original_key.lower().endswith(new_extension.lower()):
                    print(f"  Skipping (already has extension '{new_extension}'): {original_key}")
                    skipped_already_correct_ext_count += 1
                    continue

                _, current_filename_ext = os.path.splitext(original_key)
                if current_filename_ext and current_filename_ext.lower() != new_extension.lower():
                    print(f"  Skipping (has a different extension '{current_filename_ext}'): {original_key}")
                    skipped_has_other_ext_count += 1
                    continue

                new_key = f"{original_key}{new_extension}"
                print(f"  Target new name: {new_key}")

                if dry_run:
                    print(f"  [DRY RUN] Would attempt to rename '{original_key}' to '{new_key}'")
                    try:
                        if check_if_object_exists(s3_client, bucket, new_key):
                            print(f"  [DRY RUN] POTENTIAL CONFLICT: Target name '{new_key}' already exists.")
                            conflict_count += 1
                        else:
                            renamed_count += 1
                    except Exception as e_check_dry_run:
                        print(f"  [DRY RUN] Error while checking potential target {new_key}: {e_check_dry_run}")
                        error_count += 1
                else:
                    try:
                        if check_if_object_exists(s3_client, bucket, new_key):
                            print(
                                f"    CONFLICT: Target name '{new_key}' already exists. Skipping rename for '{original_key}'.")
                            conflict_count += 1
                            continue

                        print(f"    Copying '{original_key}' to '{new_key}'...")
                        copy_source = {'Bucket': bucket, 'Key': original_key}
                        s3_client.copy_object(
                            Bucket=bucket,
                            CopySource=copy_source,
                            Key=new_key
                        )
                        print(f"    Successfully copied to '{new_key}'.")

                        print(f"    Deleting original '{original_key}'...")
                        s3_client.delete_object(Bucket=bucket, Key=original_key)
                        print(f"    Successfully deleted original '{original_key}'.")
                        renamed_count += 1

                    except ClientError as e_boto:
                        print(f"    ERROR during rename operation for '{original_key}': {e_boto}")
                        error_count += 1
                    except Exception as e_unexpected:
                        print(f"    UNEXPECTED ERROR during rename for '{original_key}': {e_unexpected}")
                        error_count += 1

    except ClientError as e_list:
        print(f"AWS ClientError occurred while listing objects: {e_list}")
        error_count += 1
    except Exception as e_generic_list:
        print(f"An unexpected error occurred while listing objects: {e_generic_list}")
        error_count += 1

    print("\n--- Renaming Summary ---")
    print(f"Files that would be/were renamed: {renamed_count}")
    print(f"Files skipped (already had '{new_extension}'): {skipped_already_correct_ext_count}")
    print(f"Files skipped (had a different existing extension): {skipped_has_other_ext_count}")
    print(f"Skipped (folder markers): {skipped_folders_count}")
    print(f"Conflicts (target name already existed): {conflict_count}")
    print(f"Errors encountered during operations: {error_count}")
    print(f"DRY RUN was: {'ENABLED' if dry_run else 'DISABLED'}")
    print("-------------------------")


if __name__ == "__main__":
    if not all([ACCESS_KEY, SECRET_KEY, REGION, ENDPOINT_URL, BUCKET_NAME]):
        print("CRITICAL ERROR: One or more DigitalOcean Spaces credentials are not set in your .env file.")
        print(
            "Please ensure DO_SPACES_KEY, DO_SPACES_SECRET, DO_SPACES_REGION, DO_SPACES_ENDPOINT, and DO_SPACES_BUCKET are correctly set.")
    elif TARGET_DO_FOLDER_PREFIX is None:
        print(f"CRITICAL ERROR: 'TARGET_DO_FOLDER_PREFIX' is not configured.")
    else:
        print(f"Attempting to connect with Endpoint: https://{ENDPOINT_URL}")
        s3_client_instance = boto3.client(
            's3',
            region_name=REGION,
            endpoint_url=f"https://{ENDPOINT_URL}",
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY
        )
        rename_files_add_extension(
            s3_client_instance,
            BUCKET_NAME,
            TARGET_DO_FOLDER_PREFIX,
            NEW_EXTENSION,
            DRY_RUN
        )