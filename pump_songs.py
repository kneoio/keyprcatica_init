#!/usr/bin/env python3
import os
import re
import json
import random
import tempfile
from datetime import datetime
from faker import Faker
from slugify import slugify
import boto3
import magic
from dotenv import load_dotenv

from cnst.const import generate_loc_name
from database import get_connection
from util.audio_metadata_parser import AudioMetadataParser
from util.logging import logger
from util.mime_utils import determine_mime_type
from util.permissions import add_default_superuser_permissions

BRAND_SLUG = "aizoo"
SONGS_TO_ADD = 500

BRAND_PREFERRED_FOLDERS = ["suno", "music", "electronic"]

MAX_FILES_PER_FOLDER = 1000
MAX_FETCH_POOL_SIZE = 100
MIME_DETECTION_READ_BYTES = 2048

fake = Faker()

load_dotenv()

access_key = os.getenv('DO_SPACES_KEY')
secret_key = os.getenv('DO_SPACES_SECRET')
region = os.getenv('DO_SPACES_REGION')
endpoint = os.getenv('DO_SPACES_ENDPOINT')
bucket_name = os.getenv('DO_SPACES_BUCKET')

if BRAND_SLUG not in ["aizoo", "bit2bit", "nitroglycerin", "labirints", "sexta", "bratan"]:
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
            logger.error(
                f"No files found in any of the configured preferred folders ({BRAND_PREFERRED_FOLDERS}). Cannot add songs.")
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
        s3_session = boto3.session.Session()
        s3_client = s3_session.client(
            's3',
            region_name=region,
            endpoint_url=f"https://{endpoint}",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        mime_detector = magic.Magic(mime=True)
        metadata_parser = AudioMetadataParser(logger)
    except Exception as e:
        logger.error(f"Failed to initialize S3 client, magic, or metadata parser: {e}")
        if cursor: cursor.close()
        if conn: conn.close()
        return

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
            logger.warning(
                "No potential files fetched from DigitalOcean Spaces based on preferred folders. Cannot add songs.")
            return

        # Check existing files in _files table instead of do_key
        cursor.execute("SELECT file_key FROM _files WHERE parent_table = 'kneobroadcaster__sound_fragments'")
        existing_db_files = {row[0] for row in cursor.fetchall()}
        logger.info(f"Found {len(existing_db_files)} existing file keys in the database.")

        # Check for existing songs by artist/title combination
        existing_songs = set()
        cursor.execute("SELECT LOWER(artist), LOWER(title) FROM kneobroadcaster__sound_fragments")
        for row in cursor.fetchall():
            existing_songs.add((row[0], row[1]))

        new_files_to_process = [f for f in potential_files if f not in existing_db_files]

        if not new_files_to_process:
            logger.info(
                "No new files found among the fetched potential files that are not already in the database. All relevant files might already be added.")
            return

        logger.info(f"Found {len(new_files_to_process)} new files among potential files to consider adding.")

        files_to_add = random.sample(new_files_to_process, min(songs_needed, len(new_files_to_process)))

        if not files_to_add:
            logger.info("Selected 0 new files to add after filtering and sampling.")
            return

        logger.info(f"Adding {len(files_to_add)} new songs to brand {brand_slug} (ID: {brand_id}).")

        added_count = 0
        for file_key in files_to_add:
            temp_audio_file_path = None
            try:
                now = datetime.now()
                folder = file_key.split('/')[0] if '/' in file_key else "root"
                filename = os.path.basename(file_key)

                # Initialize metadata variables
                meta_artist = None
                meta_title = None
                meta_album = None

                # Try to parse metadata from the actual audio file
                try:
                    file_suffix = os.path.splitext(filename)[1]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix) as tmp_f:
                        s3_client.download_fileobj(bucket_name, file_key, tmp_f)
                        temp_audio_file_path = tmp_f.name

                    parsed_meta = metadata_parser.parse_metadata(temp_audio_file_path)
                    if parsed_meta:
                        meta_artist = parsed_meta.get("artist")
                        meta_title = parsed_meta.get("title")
                        meta_album = parsed_meta.get("album")

                    if meta_artist or meta_title or meta_album:
                        logger.info(
                            f"Metadata for '{filename}': Artist='{meta_artist}', Title='{meta_title}', Album='{meta_album}'")
                except Exception as e_meta_dl:
                    logger.error(f"Error downloading or parsing metadata for '{file_key}': {e_meta_dl}")
                finally:
                    if temp_audio_file_path and os.path.exists(temp_audio_file_path):
                        try:
                            os.remove(temp_audio_file_path)
                            temp_audio_file_path = None  # Reset to avoid cleanup issues
                        except OSError as e_remove:
                            logger.warning(f"Could not remove temp metadata file '{temp_audio_file_path}': {e_remove}")

                # Parse from filename as fallback
                match = re.match(r'^(?:\d+\.\s*)?(.*?)\s+-\s+(.*?)(?:\.mp3|\.wav)$', filename, re.IGNORECASE)
                fn_artist = match.group(1).strip() if match and match.group(1) else ""
                fn_title = match.group(2).strip() if match and match.group(2) else os.path.splitext(filename)[0]

                # Use metadata if available, otherwise fallback to filename parsing
                final_artist = meta_artist if meta_artist is not None else fn_artist
                final_title = meta_title if meta_title is not None else fn_title
                final_album = meta_album if meta_album is not None else ""

                # Clean up artist if it's just a number (and not from metadata)
                if final_artist and final_artist.isdigit() and not meta_artist:
                    final_artist = ""

                # Ensure we have values
                final_artist = final_artist if final_artist else ""
                final_title = final_title if final_title else os.path.splitext(filename)[0]

                # Generate fake artist if empty
                if not final_artist:
                    final_artist = fake.name()
                    logger.warning(
                        f"Could not parse artist from '{filename}' in folder '{folder}', using faker name: {final_artist}")

                if not final_title:
                    final_title = f"Unknown Title - {os.path.splitext(filename)[0]}"
                    logger.warning(
                        f"Could not parse title from '{filename}' in folder '{folder}', using fallback title: {final_title}")

                logger.debug(
                    f"Consolidated for '{filename}': Artist='{final_artist}', Title='{final_title}', Album='{final_album}'")

                # Check for duplicate songs
                song_key = (final_artist.lower(), final_title.lower())
                if song_key in existing_songs:
                    logger.warning(
                        f"Skipping duplicate song (Artist/Title): '{final_artist}' - '{final_title}' from file '{file_key}'")
                    continue

                # Determine MIME type
                mime_type = determine_mime_type(
                    s3_client=s3_client,
                    bucket_name=bucket_name,
                    file_key=file_key,
                    filename=filename,
                    mime_detector=mime_detector,
                    logger=logger,
                    read_bytes=MIME_DETECTION_READ_BYTES
                )

                slug_name = slugify(final_title) or f"fragment-{random.randint(1000, 9999)}"
                genre = "electronic"
                loc_name = generate_loc_name(final_title, final_title, final_title)
                add_info = {"source": "DigitalOcean Spaces Import", "original_file": file_key}

                # First insert the sound fragment record
                cursor.execute("""
                    INSERT INTO kneobroadcaster__sound_fragments
                    (author, reg_date, last_mod_user, last_mod_date, source, status, type,
                     title, artist, genre, album, loc_name, add_info, slug_name, archived)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (
                    0, now, 0, now, "USERS_UPLOAD", 1, "SONG",
                    final_title, final_artist, genre, final_album,
                    json.dumps(loc_name), json.dumps(add_info), slug_name, 0
                ))
                fragment_id = cursor.fetchone()[0]

                # Then insert the file record
                cursor.execute("""
                    INSERT INTO _files 
                    (reg_date, last_mod_date, parent_table, parent_id, archived,
                    storage_type, mime_type, slug_name, file_original_name, file_key)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    now, now,
                    'kneobroadcaster__sound_fragments', fragment_id, 0,
                    'DIGITAL_OCEAN', mime_type, slug_name, filename, file_key
                ))

                # Link to brand
                cursor.execute("""
                    INSERT INTO kneobroadcaster__brand_sound_fragments
                    (brand_id, sound_fragment_id, played_by_brand_count, last_time_played_by_brand)
                    VALUES (%s, %s, %s, %s)
                """, (brand_id, fragment_id, 0, None))

                # Add random label (optional)
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

                # Add random reader (optional)
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

                # Add default superuser permissions
                add_default_superuser_permissions(cursor, fragment_id, "kneobroadcaster__sound_fragment_readers")

                # Update tracking sets
                existing_db_files.add(file_key)
                existing_songs.add(song_key)

                logger.info(
                    f"Added song fragment for file '{filename}' from folder '{folder}' (ID: {fragment_id}): '{final_title}' by '{final_artist}' (Album: '{final_album}', MIME: {mime_type})")
                added_count += 1

            except Exception as e:
                logger.error(f"Error processing file {file_key}: {e}")
                conn.rollback()
            finally:
                # Final cleanup of temp file
                if temp_audio_file_path and os.path.exists(temp_audio_file_path):
                    try:
                        os.remove(temp_audio_file_path)
                    except OSError as e_final_remove:
                        logger.warning(
                            f"Final cleanup: Could not remove temp metadata file '{temp_audio_file_path}': {e_final_remove}")

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