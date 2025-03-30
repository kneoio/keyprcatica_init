import os
import re
import json
import random
from datetime import datetime
from faker import Faker
from slugify import slugify
import boto3
from dotenv import load_dotenv

from cnst.const import generate_loc_name
from database import get_connection
from util.logging import logger
from util.permissions import add_superuser_permissions

fake = Faker()

# Load environment variables from .env file
load_dotenv()

# Get environment variables for DigitalOcean Spaces
access_key = os.getenv('DO_SPACES_KEY')
secret_key = os.getenv('DO_SPACES_SECRET')
region = os.getenv('DO_SPACES_REGION')
endpoint = os.getenv('DO_SPACES_ENDPOINT')
bucket_name = os.getenv('DO_SPACES_BUCKET')

# Configuration parameters
SONGS_PER_BRAND = 50  # Number of songs to add per radio station
MAX_FILES_TO_FETCH = 100  # Maximum number of files to fetch from storage
MAX_FILES_PER_FOLDER = 10  # Maximum files to select from each folder
NUM_FOLDERS_TO_SELECT = 3  # Number of folders to randomly select


# Change 1: Modify the get_files_from_do_spaces function to get more files
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

            # If folders exist, randomly select files and folders
            if folders:
                # Decide whether to pick from specific folders
                use_folders = random.choice([True, False])

                if use_folders and folders:
                    # Select random folders
                    selected_folders = random.sample(folders, min(NUM_FOLDERS_TO_SELECT, len(folders)))
                    selected_files = []

                    # Get files from the selected folders
                    for folder in selected_folders:
                        folder_files = [f for f in files if f.startswith(folder)]
                        if folder_files:
                            folder_selection = random.sample(folder_files, min(MAX_FILES_PER_FOLDER, len(folder_files)))
                            selected_files.extend(folder_selection)

                    # If we didn't get enough files from folders, add some random ones
                    if len(selected_files) < MAX_FILES_TO_FETCH and files:
                        additional_files = random.sample(
                            [f for f in files if f not in selected_files],
                            min(MAX_FILES_TO_FETCH - len(selected_files), len(files) - len(selected_files))
                        )
                        selected_files.extend(additional_files)

                    return selected_files

            # Default: return random files from the entire bucket
            return random.sample(files, min(MAX_FILES_TO_FETCH, len(files)))
        else:
            logger.warning("No files found in the bucket.")
            return []
    except Exception as e:
        logger.error(f"Failed to fetch files from DigitalOcean Spaces: {e}")
        return []


# Change 2: Modify the generate_sound_fragments function to add songs per station and check for duplicates
def generate_sound_fragments():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM kneobroadcaster__brands")
    brand_ids = [row[0] for row in cursor.fetchall()]

    if not brand_ids:
        logger.warning("No brands found in the database. Skipping brand-sound fragment binding.")
        return

    files = get_files_from_do_spaces()

    # Get existing files to avoid duplicates
    cursor.execute("SELECT do_key FROM kneobroadcaster__sound_fragments WHERE do_key IS NOT NULL")
    existing_files = {row[0] for row in cursor.fetchall()}

    # Filter out files that are already in the database
    new_files = [f for f in files if f not in existing_files]

    if not new_files:
        logger.info("No new files found to process. All files have already been added.")
        conn.close()
        return

    logger.info(f"Found {len(new_files)} new files to process out of {len(files)} total files.")

    # Each brand should get approximately SONGS_PER_BRAND songs
    for brand_id in brand_ids:
        # Count existing songs for this brand
        cursor.execute("""
            SELECT COUNT(*) FROM kneobroadcaster__brand_sound_fragments
            WHERE brand_id = %s
        """, (brand_id,))
        existing_songs_count = cursor.fetchone()[0]

        logger.info(f"Brand {brand_id} already has {existing_songs_count} songs.")

        # Skip if the brand already has enough songs
        if existing_songs_count >= SONGS_PER_BRAND:
            logger.info(
                f"Brand {brand_id} already has {existing_songs_count} songs, which is >= {SONGS_PER_BRAND}. Skipping.")
            continue

        # Calculate how many more songs we need to add
        songs_to_add = min(SONGS_PER_BRAND - existing_songs_count, len(new_files))

        if songs_to_add <= 0:
            logger.info(f"No more songs needed for brand {brand_id}.")
            continue

        logger.info(f"Adding {songs_to_add} songs to brand {brand_id}.")

        # Select random files for this brand
        brand_files = random.sample(new_files, songs_to_add)

        for file_key in brand_files:
            try:
                now = datetime.now()

                match = re.match(r'^\d+\.\s+(.*?)\s+-\s+(.*?)\.mp3$', file_key, re.IGNORECASE)
                if match:
                    artist = match.group(1).strip()
                    title = match.group(2).strip()
                else:
                    title = os.path.splitext(file_key)[0]
                    artist = ""

                slug_name = slugify(title)
                genre = fake.word()
                album = fake.word()
                loc_name = generate_loc_name(title, title, title)
                add_info = {"source": "DigitalOcean Spaces"}

                # Insert the file key into the do_key field
                do_key = file_key

                cursor.execute("""
                    INSERT INTO kneobroadcaster__sound_fragments 
                    (author, reg_date, last_mod_user, last_mod_date, source, status, type, title, artist, genre, album, loc_name, add_info, slug_name, do_key, archived)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (
                    0, now, 0, now, "DIGITALOCEAN", 1, "SONG",
                    title, artist, genre, album, json.dumps(loc_name), json.dumps(add_info), slug_name, do_key, 0
                ))
                fragment_id = cursor.fetchone()[0]

                # Associate this fragment with the current brand
                cursor.execute("""
                    INSERT INTO kneobroadcaster__brand_sound_fragments 
                    (brand_id, sound_fragment_id, played_by_brand_count, last_time_played_by_brand)
                    VALUES (%s, %s, %s, %s)
                """, (brand_id, fragment_id, 0, None))

                cursor.execute("SELECT id FROM __labels ORDER BY RANDOM() LIMIT 1")
                label = cursor.fetchone()
                if label:
                    cursor.execute("""
                        INSERT INTO kneobroadcaster__sound_fragment_labels 
                        (id, label_id)
                        VALUES (%s, %s)
                    """, (fragment_id, label[0]))

                cursor.execute("SELECT id FROM _users ORDER BY RANDOM() LIMIT 1")
                reader = cursor.fetchone()
                if reader:
                    cursor.execute("""
                        INSERT INTO kneobroadcaster__sound_fragment_readers 
                        (reader, entity_id, can_edit, can_delete, reading_time)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (reader[0], fragment_id, False, False, now))

                add_superuser_permissions(cursor, fragment_id, "kneobroadcaster__sound_fragment_readers")

                logger.info(f"Sound fragment inserted for file: {file_key} and brand: {brand_id}")
            except Exception as e:
                logger.error(f"Error processing file {file_key} for brand {brand_id}: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting sound fragments and binding them to brands.")