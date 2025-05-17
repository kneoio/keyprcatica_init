#!/usr/bin/env python3
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

BRAND_SLUG = "nitroglycerin"
SONGS_TO_ADD = 500


BRAND_PREFERRED_FOLDERS = ["suno", "2", "3", "6", "7", "8"]

MAX_FILES_PER_FOLDER = 1000
MAX_FETCH_POOL_SIZE = 100


fake = Faker()

load_dotenv()

access_key = os.getenv('DO_SPACES_KEY')
secret_key = os.getenv('DO_SPACES_SECRET')
region = os.getenv('DO_SPACES_REGION')
endpoint = os.getenv('DO_SPACES_ENDPOINT')
bucket_name = os.getenv('DO_SPACES_BUCKET')

if BRAND_SLUG not in ["nunoscope", "aidazoo", "nitroglycerin", "fock-fock", "klentara", "enacone"]:
    logger.error(f"BRAND_SLUG '{BRAND_SLUG}' is not a recognized static brand.")
    exit(1)


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

        response = client.list_objects_v2(Bucket=bucket_name)
        all_audio_files = []

        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                if not key.endswith('/') and key.lower().endswith(('.mp3', '.wav')):
                    all_audio_files.append(key)

        if not all_audio_files:
            logger.warning("No audio files found in the bucket.")
            return []

        logger.info(f"Found {len(all_audio_files)} total audio files in the bucket.")

        brand_files = []

        logger.info(f"Fetching files specifically from folders: {BRAND_PREFERRED_FOLDERS}")

        for folder in BRAND_PREFERRED_FOLDERS:
            folder_prefix = f"{folder}/"
            folder_files = [f for f in all_audio_files if f.startswith(folder_prefix)]

            if folder_files:
                selected_files = folder_files[:MAX_FILES_PER_FOLDER]
                brand_files.extend(selected_files)
                logger.info(f"Found and selected {len(selected_files)} audio files from preferred folder '{folder}'.")
            else:
                 logger.warning(f"No audio files found in preferred folder '{folder}'.")


        if not brand_files:
            logger.error(f"No files found in any of the configured preferred folders ({BRAND_PREFERRED_FOLDERS}). Cannot add songs.")
            return []


        logger.info(f"Collected {len(brand_files)} potential files from preferred folders.")
        return brand_files[:MAX_FETCH_POOL_SIZE]


    except Exception as e:
        logger.error(f"Failed to fetch files from DigitalOcean Spaces: {e}")
        return []


def add_songs_to_brand(brand_slug):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM kneobroadcaster__brands WHERE slug_name = %s", (brand_slug,))
        brand_row = cursor.fetchone()

        if not brand_row:
            logger.error(f"Brand with slug name '{brand_slug}' does not exist in the database. Cannot add songs.")
            return

        brand_id = brand_row[0]
        logger.info(f"Found brand ID {brand_id} for slug '{brand_slug}'.")

        cursor.execute("""
            SELECT COUNT(*) FROM kneobroadcaster__brand_sound_fragments
            WHERE brand_id = %s
        """, (brand_id,))
        existing_songs_count = cursor.fetchone()[0]

        logger.info(f"Brand {brand_slug} (ID: {brand_id}) already has {existing_songs_count} songs associated.")

        songs_needed = max(0, SONGS_TO_ADD - existing_songs_count)

        if songs_needed <= 0:
            logger.info(
                f"Brand {brand_slug} (ID: {brand_id}) already has {existing_songs_count} songs, which is >= {SONGS_TO_ADD}. No more songs needed for this brand.")
            return

        logger.info(f"Attempting to add {songs_needed} more songs to brand {brand_slug}.")

        potential_files = get_files_from_do_spaces()

        if not potential_files:
            logger.warning("No potential files fetched from DigitalOcean Spaces based on preferred folders. Cannot add songs.")
            return

        cursor.execute("SELECT do_key FROM kneobroadcaster__sound_fragments WHERE do_key IS NOT NULL")
        existing_db_files = {row[0] for row in cursor.fetchall()}
        logger.info(f"Found {len(existing_db_files)} existing file keys in the database.")


        new_files_to_process = [f for f in potential_files if f not in existing_db_files]

        if not new_files_to_process:
            logger.info("No new files found among the fetched potential files that are not already in the database. All relevant files might already be added.")
            return

        logger.info(f"Found {len(new_files_to_process)} new files among potential files to consider adding.")

        files_to_add = random.sample(new_files_to_process, min(songs_needed, len(new_files_to_process)))

        if not files_to_add:
            logger.info("Selected 0 new files to add after filtering and sampling.")
            return

        logger.info(f"Adding {len(files_to_add)} new songs to brand {brand_slug} (ID: {brand_id}).")

        added_count = 0
        for file_key in files_to_add:
            try:
                now = datetime.now()
                folder = file_key.split('/')[0] if '/' in file_key else "root"

                filename = os.path.basename(file_key)
                match = re.match(r'^(?:\d+\.\s*)?(.*?)\s+-\s+(.*?)(?:\.mp3|\.wav)$', filename, re.IGNORECASE)
                artist = match.group(1).strip() if match else ""
                title = match.group(2).strip() if match else os.path.splitext(filename)[0]

                if artist and artist.isdigit():
                    artist = ""

                if not artist:
                    artist = fake.name()
                    logger.warning(f"Could not parse artist from '{filename}' in folder '{folder}', using faker name: {artist}")

                if not title:
                    title = f"Unknown Title - {os.path.splitext(filename)[0]}"
                    logger.warning(f"Could not parse title from '{filename}' in folder '{folder}', using fallback title: {title}")


                slug_name = slugify(title) or f"fragment-{random.randint(1000, 9999)}"
                genre = "electronic"
                album = fake.word()
                loc_name = generate_loc_name(title, title, title)
                add_info = {"source": "DigitalOcean Spaces Import", "original_file": file_key}


                cursor.execute("""
                    INSERT INTO kneobroadcaster__sound_fragments
                    (author, reg_date, last_mod_user, last_mod_date, source, status, type,
                     title, artist, genre, album, loc_name, add_info, slug_name, do_key, archived)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (
                    0, now, 0, now, "DIGITALOCEAN", 1, "SONG",
                    title, artist, genre, album, json.dumps(loc_name), json.dumps(add_info), slug_name, file_key, 0
                ))
                fragment_id = cursor.fetchone()[0]

                cursor.execute("""
                    INSERT INTO kneobroadcaster__brand_sound_fragments
                    (brand_id, sound_fragment_id, played_by_brand_count, last_time_played_by_brand)
                    VALUES (%s, %s, %s, %s)
                """, (brand_id, fragment_id, 0, None))

                cursor.execute("SELECT id FROM __labels ORDER BY RANDOM() LIMIT 1")
                label = cursor.fetchone()
                if label:
                    try:
                        cursor.execute("""
                            INSERT INTO kneobroadcaster__sound_fragment_labels
                            (id, label_id)
                            VALUES (%s, %s)
                        """, (fragment_id, label[0]))
                    except Exception as label_e:
                        logger.warning(f"Failed to add random label for fragment {fragment_id}: {label_e}")


                cursor.execute("SELECT id FROM _users ORDER BY RANDOM() LIMIT 1")
                reader = cursor.fetchone()
                if reader:
                    try:
                        cursor.execute("""
                            INSERT INTO kneobroadcaster__sound_fragment_readers
                            (reader, entity_id, can_edit, can_delete, reading_time)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (reader[0], fragment_id, False, False, now))
                    except Exception as reader_e:
                         logger.warning(f"Failed to add random reader for fragment {fragment_id}: {reader_e}")


                add_default_superuser_permissions(cursor, fragment_id, "kneobroadcaster__sound_fragment_readers")

                logger.info(f"Added song fragment for file '{filename}' from folder '{folder}' (ID: {fragment_id}).")
                added_count += 1

            except Exception as e:
                logger.error(f"Error processing file {file_key}: {e}")
                conn.rollback()

        conn.commit()
        logger.info(f"Finished adding process. Successfully added {added_count} songs to brand {brand_slug}.")

    except Exception as main_e:
        logger.error(f"An error occurred during the main process for brand {brand_slug}: {main_e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    logger.info(f"Starting script to add songs to brand with slug: {BRAND_SLUG}")
    add_songs_to_brand(BRAND_SLUG)
    logger.info(f"Script finished for brand: {BRAND_SLUG}")