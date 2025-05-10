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

# Static brand configuration - maps brand names to their preferred folders
STATIC_BRAND_CONFIG = {
    "Nunoscope": ["suno/", "2/", "3/", "6/", "/7", "/8"],
    "Aidazoo": ["suno/", "2/", "3/", "4/", "5/", "6/", "/7", "/8"],
}


def get_files_from_do_spaces(brand_name=None):
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
                # Skip directories
                if key.endswith('/'):
                    continue
                # Check file extension
                if key.lower().endswith(('.mp3', '.wav')):
                    files.append(key)
                    # Add parent folders
                    parts = key.split('/')
                    if len(parts) > 1:
                        folder = '/'.join(parts[:-1]) + '/'
                        folders.add(folder)

            folders = list(folders)

            # If this is a static brand with preferred folders
            if brand_name and brand_name in STATIC_BRAND_CONFIG:
                preferred_folders = STATIC_BRAND_CONFIG[brand_name]
                brand_files = []

                # Get files from preferred folders first
                for folder in preferred_folders:
                    folder_files = [f for f in files if f.startswith(folder)]
                    if folder_files:
                        brand_files.extend(random.sample(
                            folder_files,
                            min(MAX_FILES_PER_FOLDER, len(folder_files))
                        ))

                # If we didn't get enough files from preferred folders, add random ones
                if len(brand_files) < MAX_FILES_TO_FETCH:
                    remaining_files = [f for f in files if f not in brand_files]
                    if remaining_files:
                        additional = random.sample(
                            remaining_files,
                            min(MAX_FILES_TO_FETCH - len(brand_files), len(remaining_files))
                        )
                        brand_files.extend(additional)

                return brand_files

            # For non-static brands or when no brand is specified
            if folders:
                # Select random folders
                selected_folders = random.sample(folders, min(NUM_FOLDERS_TO_SELECT, len(folders)))
                selected_files = []

                for folder in selected_folders:
                    folder_files = [f for f in files if f.startswith(folder)]
                    if folder_files:
                        selected_files.extend(random.sample(
                            folder_files,
                            min(MAX_FILES_PER_FOLDER, len(folder_files))
                        ))

                if len(selected_files) < MAX_FILES_TO_FETCH:
                    remaining_files = [f for f in files if f not in selected_files]
                    if remaining_files:
                        additional = random.sample(
                            remaining_files,
                            min(MAX_FILES_TO_FETCH - len(selected_files), len(remaining_files))
                        )
                        selected_files.extend(additional)

                return selected_files

            # Default: return random files from the entire bucket
            return random.sample(files, min(MAX_FILES_TO_FETCH, len(files)))
        else:
            logger.warning("No files found in the bucket.")
            return []
    except Exception as e:
        logger.error(f"Failed to fetch files from DigitalOcean Spaces: {e}")
        return []


def generate_sound_fragments():
    conn = get_connection()
    cursor = conn.cursor()

    # Get brands with their names
    cursor.execute("SELECT id, loc_name FROM kneobroadcaster__brands")
    brands = cursor.fetchall()

    if not brands:
        logger.warning("No brands found in the database. Skipping brand-sound fragment binding.")
        return

    # Get existing files to avoid duplicates
    cursor.execute("SELECT do_key FROM kneobroadcaster__sound_fragments WHERE do_key IS NOT NULL")
    existing_files = {row[0] for row in cursor.fetchall()}

    for brand_id, loc_name_data in brands:
        brand_name = ""
        try:
            # Handle both string and dict loc_name cases
            if isinstance(loc_name_data, str):
                loc_name = json.loads(loc_name_data)
            else:
                loc_name = loc_name_data

            brand_name = loc_name.get('eng', str(brand_id))  # Default to brand_id if no name

            # Get files specific to this brand
            files = get_files_from_do_spaces(brand_name if brand_name in STATIC_BRAND_CONFIG else None)

            # Filter out files that are already in the database
            new_files = [f for f in files if f not in existing_files]

            if not new_files:
                logger.info(f"No new files found for brand {brand_name}. Skipping.")
                continue

            # Count existing songs for this brand
            cursor.execute("""
                SELECT COUNT(*) FROM kneobroadcaster__brand_sound_fragments
                WHERE brand_id = %s
            """, (brand_id,))
            existing_songs_count = cursor.fetchone()[0]

            logger.info(f"Brand {brand_name} has {existing_songs_count} existing songs.")

            # Calculate how many more songs we need to add
            songs_to_add = min(SONGS_PER_BRAND - existing_songs_count, len(new_files))

            if songs_to_add <= 0:
                logger.info(f"Brand {brand_name} already has enough songs. Skipping.")
                continue

            logger.info(f"Adding {songs_to_add} songs to brand {brand_name}.")

            # Select random files for this brand
            brand_files = random.sample(new_files, songs_to_add)

            for file_key in brand_files:
                try:
                    now = datetime.now()

                    # Extract artist and title from filename (supports both MP3 and WAV)
                    filename = os.path.basename(file_key)
                    match = re.match(r'^(?:\d+\.\s*)?(.*?)\s+-\s+(.*?)(?:\.mp3|\.wav)$', filename, re.IGNORECASE)
                    if match:
                        artist = match.group(1).strip()
                        title = match.group(2).strip()
                    else:
                        title = os.path.splitext(filename)[0]
                        artist = ""

                    slug_name = slugify(title)
                    genre = "electronic"
                    album = fake.word()
                    loc_name = generate_loc_name(title, title, title)
                    add_info = {"source": "Imported automatically"}

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

                    # Add the file to existing_files to prevent duplicates in this run
                    existing_files.add(file_key)

                    logger.info(f"Added sound fragment: {title} by {artist} to brand {brand_name}")
                except Exception as e:
                    logger.error(f"Error processing file {file_key} for brand {brand_name}: {e}")
                    conn.rollback()

            conn.commit()
        except Exception as e:
            logger.error(f"Error processing brand {brand_name or brand_id}: {e}")
            conn.rollback()

    cursor.close()
    conn.close()
    logger.info("Finished inserting sound fragments and binding them to brands.")