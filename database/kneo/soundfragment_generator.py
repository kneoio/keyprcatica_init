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
from util.permissions import add_default_superuser_permissions

fake = Faker()

# Load environment variables
load_dotenv()

# DigitalOcean Spaces config
access_key = os.getenv('DO_SPACES_KEY')
secret_key = os.getenv('DO_SPACES_SECRET')
region = os.getenv('DO_SPACES_REGION')
endpoint = os.getenv('DO_SPACES_ENDPOINT')
bucket_name = os.getenv('DO_SPACES_BUCKET')

# Configuration
SONGS_PER_BRAND = 50
MAX_FILES_TO_FETCH = 100
MAX_FILES_PER_FOLDER = 10
NUM_FOLDERS_TO_SELECT = 3

# Static brand folder mappings (using slug_names as keys)
STATIC_BRAND_CONFIG = {
    "nunoscope": ["suno", "2", "3", "6", "7", "8"],
    "aidazoo": ["suno", "2", "3", "4", "5", "6", "7", "8"],
    "nitroglycerin": ["suno", "2", "3", "6", "7", "8"],
    "fock-fock": ["suno", "6", "7", "8"],
    "klentara": ["suno", "2", "3", "4", "5", "6", "7", "8"],
    "enacone": ["4", "5"],
}


def get_files_from_do_spaces(brand_slug=None):
    """Fetch files from DigitalOcean Spaces with strict folder matching for static brands"""
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
                if not key.endswith('/') and key.lower().endswith(('.mp3', '.wav')):
                    files.append(key)

            # If this is a static brand with preferred folders
            if brand_slug and brand_slug in STATIC_BRAND_CONFIG:
                preferred_folders = STATIC_BRAND_CONFIG[brand_slug]
                brand_files = []

                for folder in preferred_folders:
                    # EXACT folder matching with trailing slash
                    folder_prefix = f"{folder}/"
                    folder_files = [f for f in files if f.startswith(folder_prefix)]

                    if folder_files:
                        # Take all files from folder, but no more than MAX_FILES_PER_FOLDER
                        selected_files = folder_files[:MAX_FILES_PER_FOLDER]
                        brand_files.extend(selected_files)
                        logger.info(f"Found {len(selected_files)} files in folder {folder} for brand {brand_slug}")

                if not brand_files:
                    logger.warning(f"No files found in preferred folders for brand {brand_slug}")
                return brand_files

            # For non-static brands or when no brand is specified
            folders = {f.split('/')[0] for f in files if '/' in f}

            if folders:
                selected_folders = random.sample(list(folders), min(NUM_FOLDERS_TO_SELECT, len(folders)))
                selected_files = []

                for folder in selected_folders:
                    folder_files = [f for f in files if f.startswith(folder + '/')]
                    if folder_files:
                        selected = random.sample(folder_files, min(MAX_FILES_PER_FOLDER, len(folder_files)))
                        selected_files.extend(selected)
                        logger.info(f"Found {len(selected)} files in folder {folder}")

                if len(selected_files) < MAX_FILES_TO_FETCH:
                    remaining_files = [f for f in files if not any(f.startswith(f + '/') for f in selected_folders)]
                    if remaining_files:
                        additional = random.sample(remaining_files,
                                                   min(MAX_FILES_TO_FETCH - len(selected_files), len(remaining_files)))
                        selected_files.extend(additional)

                return selected_files

            return random.sample(files, min(MAX_FILES_TO_FETCH, len(files)))
        return []
    except Exception as e:
        logger.error(f"Failed to fetch files: {e}")
        return []


def generate_sound_fragments():
    """Generate sound fragments with strict folder enforcement for static brands"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Get all brands with their IDs and slug_names
        cursor.execute("""
            SELECT b.id, b.slug_name 
            FROM kneobroadcaster__brands b
            WHERE b.slug_name IN %s
        """, (tuple(STATIC_BRAND_CONFIG.keys()),))
        static_brands = cursor.fetchall()

        cursor.execute("""
            SELECT b.id, b.slug_name 
            FROM kneobroadcaster__brands b
            WHERE b.slug_name NOT IN %s OR b.slug_name IS NULL
        """, (tuple(STATIC_BRAND_CONFIG.keys()),))
        non_static_brands = cursor.fetchall()

        # Track existing songs by (artist, title) to prevent duplicates
        existing_songs = set()
        cursor.execute("SELECT LOWER(artist), LOWER(title) FROM kneobroadcaster__sound_fragments")
        for row in cursor.fetchall():
            existing_songs.add((row[0], row[1]))

        # Track existing file keys
        cursor.execute("SELECT do_key FROM kneobroadcaster__sound_fragments WHERE do_key IS NOT NULL")
        existing_files = {row[0] for row in cursor.fetchall()}

        # Process static brands first with strict folder matching
        for brand_id, brand_slug in static_brands:
            try:
                logger.info(f"\nProcessing static brand: {brand_slug} (ID: {brand_id})")

                # Get files specific to this brand's folders
                files = get_files_from_do_spaces(brand_slug)
                new_files = [f for f in files if f not in existing_files]

                if not new_files:
                    logger.info(f"No new files for brand {brand_slug}")
                    continue

                # Count existing songs for this brand
                cursor.execute("""
                    SELECT COUNT(*) FROM kneobroadcaster__brand_sound_fragments
                    WHERE brand_id = %s
                """, (brand_id,))
                existing_count = cursor.fetchone()[0]
                songs_to_add = max(0, SONGS_PER_BRAND - existing_count)

                added_count = 0
                for file_key in new_files:
                    if added_count >= songs_to_add:
                        break

                    try:
                        filename = os.path.basename(file_key)
                        folder = file_key.split('/')[0]  # Get folder name for logging

                        # Parse artist and title
                        match = re.match(r'^(?:\d+\.\s*)?(.*?)\s+-\s+(.*?)(?:\.mp3|\.wav)$', filename, re.IGNORECASE)
                        artist = match.group(1).strip() if match else ""
                        title = match.group(2).strip() if match else os.path.splitext(filename)[0]

                        if artist and artist.isdigit():
                            artist = ""

                        # Skip duplicates
                        song_key = (artist.lower(), title.lower())
                        if song_key in existing_songs:
                            logger.warning(f"Skipping duplicate: {artist} - {title} from folder {folder}")
                            continue

                        # Insert sound fragment
                        now = datetime.now()
                        song_slug = slugify(title)
                        loc_name = generate_loc_name(title, title, title)

                        cursor.execute("""
                            INSERT INTO kneobroadcaster__sound_fragments 
                            (author, reg_date, last_mod_user, last_mod_date, source, status, type, 
                             title, artist, genre, album, loc_name, add_info, slug_name, do_key, archived)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                        """, (
                            0, now, 0, now, "DIGITALOCEAN", 1, "SONG",
                            title, artist, "electronic", fake.word(),
                            json.dumps(loc_name), json.dumps({"source": "Imported"}),
                            song_slug, file_key, 0
                        ))
                        fragment_id = cursor.fetchone()[0]

                        # Associate with brand
                        cursor.execute("""
                            INSERT INTO kneobroadcaster__brand_sound_fragments 
                            (brand_id, sound_fragment_id, played_by_brand_count, last_time_played_by_brand)
                            VALUES (%s, %s, %s, %s)
                        """, (brand_id, fragment_id, 0, None))

                        # Add permissions
                        add_default_superuser_permissions(cursor, fragment_id, "kneobroadcaster__sound_fragment_readers")

                        # Update tracking sets
                        existing_files.add(file_key)
                        existing_songs.add(song_key)
                        added_count += 1

                        logger.info(f"Added {artist} - {title} from folder {folder} to brand {brand_slug}")

                    except Exception as e:
                        logger.error(f"Error processing {file_key}: {str(e)}")
                        conn.rollback()

                conn.commit()
                logger.info(f"Added {added_count} songs to brand {brand_slug}")

            except Exception as e:
                logger.error(f"Error processing brand {brand_slug}: {str(e)}")
                conn.rollback()

        # Process non-static brands
        for brand_id, brand_slug in non_static_brands:
            try:
                display_name = brand_slug if brand_slug else f"ID:{brand_id}"
                logger.info(f"\nProcessing non-static brand: {display_name}")

                # Get random files
                files = get_files_from_do_spaces()
                new_files = [f for f in files if f not in existing_files]

                if not new_files:
                    logger.info(f"No new files for brand {display_name}")
                    continue

                # Count existing songs for this brand
                cursor.execute("""
                    SELECT COUNT(*) FROM kneobroadcaster__brand_sound_fragments
                    WHERE brand_id = %s
                """, (brand_id,))
                existing_count = cursor.fetchone()[0]
                songs_to_add = max(0, SONGS_PER_BRAND - existing_count)

                added_count = 0
                for file_key in new_files:
                    if added_count >= songs_to_add:
                        break

                    try:
                        filename = os.path.basename(file_key)
                        folder = file_key.split('/')[0]  # Get folder name

                        # Parse artist and title
                        match = re.match(r'^(?:\d+\.\s*)?(.*?)\s+-\s+(.*?)(?:\.mp3|\.wav)$', filename, re.IGNORECASE)
                        artist = match.group(1).strip() if match else ""
                        title = match.group(2).strip() if match else os.path.splitext(filename)[0]

                        # Skip duplicates
                        song_key = (artist.lower(), title.lower())
                        if song_key in existing_songs:
                            logger.warning(f"Skipping duplicate: {artist} - {title} from folder {folder}")
                            continue

                        # Insert sound fragment
                        now = datetime.now()
                        song_slug = slugify(title)
                        loc_name = generate_loc_name(title, title, title)

                        cursor.execute("""
                            INSERT INTO kneobroadcaster__sound_fragments 
                            (author, reg_date, last_mod_user, last_mod_date, source, status, type, 
                             title, artist, genre, album, loc_name, add_info, slug_name, do_key, archived)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                        """, (
                            0, now, 0, now, "DIGITALOCEAN", 1, "SONG",
                            title, artist, "electronic", fake.word(),
                            json.dumps(loc_name), json.dumps({"source": "Imported"}),
                            song_slug, file_key, 0
                        ))
                        fragment_id = cursor.fetchone()[0]

                        # Associate with brand
                        cursor.execute("""
                            INSERT INTO kneobroadcaster__brand_sound_fragments 
                            (brand_id, sound_fragment_id, played_by_brand_count, last_time_played_by_brand)
                            VALUES (%s, %s, %s, %s)
                        """, (brand_id, fragment_id, 0, None))

                        # Add permissions
                        add_default_superuser_permissions(cursor, fragment_id, "kneobroadcaster__sound_fragment_readers")

                        # Update tracking sets
                        existing_files.add(file_key)
                        existing_songs.add(song_key)
                        added_count += 1

                        logger.info(f"Added {artist} - {title} from folder {folder} to brand {display_name}")

                    except Exception as e:
                        logger.error(f"Error processing {file_key}: {str(e)}")
                        conn.rollback()

                conn.commit()
                logger.info(f"Added {added_count} songs to brand {display_name}")

            except Exception as e:
                logger.error(f"Error processing brand {display_name}: {str(e)}")
                conn.rollback()

    finally:
        cursor.close()
        conn.close()

    logger.info("\nFinished processing all brands")


if __name__ == "__main__":
    generate_sound_fragments()