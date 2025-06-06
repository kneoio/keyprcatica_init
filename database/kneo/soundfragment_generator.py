import json
import os
import random
import re
import tempfile
from datetime import datetime

import boto3
import magic
from dotenv import load_dotenv
from faker import Faker
from slugify import slugify

from cnst.const import generate_loc_name
from database import get_connection
from util.audio_metadata_parser import AudioMetadataParser
from util.logging import logger
from util.mime_utils import determine_mime_type
from util.permissions import add_default_superuser_permissions

fake = Faker()

load_dotenv()

access_key = os.getenv('DO_SPACES_KEY')
secret_key = os.getenv('DO_SPACES_SECRET')
region = os.getenv('DO_SPACES_REGION')
endpoint = os.getenv('DO_SPACES_ENDPOINT')
bucket_name = os.getenv('DO_SPACES_BUCKET')

SONGS_PER_BRAND = 50
MAX_FILES_TO_FETCH = 100
MAX_FILES_PER_FOLDER = 10
NUM_FOLDERS_TO_SELECT = 3
MIME_DETECTION_READ_BYTES = 2048

STATIC_BRAND_CONFIG = {
    #"nunoscope": ["suno", "2", "3", "6", "7", "8"],
    #"aidazoo": ["suno", "2", "3", "4", "5", "6", "7", "8"],
    "nitroglycerin": ["house"],
    #"fock-fock": ["suno", "6", "7", "8"],
    #"klentara": ["suno", "2", "3", "4", "5", "6", "7", "8"],
    #"enacone": ["4", "5"],
}

def _upload_to_spaces(file_path: str, destination_key: str) -> bool:
    """Upload file to DO Spaces"""
    try:
        s3_session = boto3.session.Session()
        s3_client = s3_session.client(
            's3', 
            region_name=region, 
            endpoint_url=f"https://{endpoint}",
            aws_access_key_id=access_key, 
            aws_secret_access_key=secret_key
        )
        s3_client.upload_file(file_path, bucket_name, destination_key)
        return True
    except Exception as e:
        logger.error(f"Failed to upload {file_path} to DO Spaces: {e}")
        return False

def get_files_from_do_spaces(brand_slug=None):
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
            if brand_slug and brand_slug in STATIC_BRAND_CONFIG:
                preferred_folders = STATIC_BRAND_CONFIG[brand_slug]
                brand_files = []
                for folder_name in preferred_folders:
                    folder_prefix = f"{folder_name}/"
                    folder_files = [f for f in files if f.startswith(folder_prefix)]
                    if folder_files:
                        selected_files = folder_files[:MAX_FILES_PER_FOLDER]
                        brand_files.extend(selected_files)
                        logger.info(f"Found {len(selected_files)} files in folder {folder_name} for brand {brand_slug}")
                if not brand_files: logger.warning(f"No files found in preferred folders for brand {brand_slug}")
                return brand_files
            folders = {f.split('/')[0] for f in files if '/' in f}
            if folders:
                selected_folders = random.sample(list(folders), min(NUM_FOLDERS_TO_SELECT, len(folders)))
                selected_files_list = []
                for folder_name in selected_folders:
                    folder_files = [f for f in files if f.startswith(folder_name + '/')]
                    if folder_files:
                        selected = random.sample(folder_files, min(MAX_FILES_PER_FOLDER, len(folder_files)))
                        selected_files_list.extend(selected)
                        logger.info(f"Found {len(selected)} files in folder {folder_name}")
                current_selected_count = len(selected_files_list)
                if current_selected_count < MAX_FILES_TO_FETCH:
                    current_selected_paths = set(selected_files_list)
                    potential_remaining_files = [
                        f for f in files
                        if f not in current_selected_paths and
                           not any(f.startswith(sel_folder + '/') for sel_folder in selected_folders)
                    ]
                    if not selected_folders and files:
                        potential_remaining_files = [f for f in files if f not in current_selected_paths]
                    if potential_remaining_files:
                        additional_needed = MAX_FILES_TO_FETCH - current_selected_count
                        additional = random.sample(
                            potential_remaining_files,
                            min(additional_needed, len(potential_remaining_files))
                        )
                        selected_files_list.extend(additional)
                        logger.info(f"Added {len(additional)} additional files.")
                return selected_files_list[:MAX_FILES_TO_FETCH]
            return random.sample(files, min(MAX_FILES_TO_FETCH, len(files))) if files else []
        return []
    except Exception as e:
        logger.error(f"Failed to fetch files: {e}")
        return []

def generate_sound_fragments():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        s3_session = boto3.session.Session()
        s3_client = s3_session.client(
            's3', region_name=region, endpoint_url=f"https://{endpoint}",
            aws_access_key_id=access_key, aws_secret_access_key=secret_key
        )
        mime_detector = magic.Magic(mime=True)
        metadata_parser = AudioMetadataParser(logger)
    except Exception as e:
        logger.error(f"Failed to initialize S3 client, magic, or metadata parser: {e}")
        if cursor: cursor.close()
        if conn: conn.close()
        return

    try:
        cursor.execute("SELECT b.id, b.slug_name FROM kneobroadcaster__brands b WHERE b.slug_name IN %s",
                       (tuple(STATIC_BRAND_CONFIG.keys()),))
        static_brands = cursor.fetchall()
        cursor.execute(
            "SELECT b.id, b.slug_name FROM kneobroadcaster__brands b WHERE b.slug_name NOT IN %s OR b.slug_name IS NULL",
            (tuple(STATIC_BRAND_CONFIG.keys()),))
        non_static_brands = cursor.fetchall()

        existing_songs = set()
        cursor.execute("SELECT LOWER(artist), LOWER(title) FROM kneobroadcaster__sound_fragments")
        for row in cursor.fetchall(): existing_songs.add((row[0], row[1]))
        
        cursor.execute("SELECT file_key FROM _files WHERE parent_table = 'kneobroadcaster__sound_fragments'")
        existing_files = {row[0] for row in cursor.fetchall()}

        brands_to_process = [("static", brand_id, slug) for brand_id, slug in static_brands] + \
                            [("non-static", brand_id, slug) for brand_id, slug in non_static_brands]

        for brand_type, brand_id, brand_slug_or_none in brands_to_process:
            brand_display_name = brand_slug_or_none if brand_slug_or_none else f"ID:{brand_id}"
            logger.info(f"\nProcessing {brand_type} brand: {brand_display_name}")

            try:
                files_for_brand = get_files_from_do_spaces(brand_slug_or_none if brand_type == "static" else None)
                new_files = [f for f in files_for_brand if f not in existing_files]

                if not new_files:
                    logger.info(f"No new files suitable for brand {brand_display_name}")
                    continue

                cursor.execute("SELECT COUNT(*) FROM kneobroadcaster__brand_sound_fragments WHERE brand_id = %s",
                               (brand_id,))
                existing_count = cursor.fetchone()[0]
                songs_to_add = max(0, SONGS_PER_BRAND - existing_count)

                if songs_to_add == 0:
                    logger.info(
                        f"Brand {brand_display_name} already has {existing_count} songs. No new songs will be added.")
                    continue

                added_count = 0
                for file_key in new_files:
                    if added_count >= songs_to_add: break

                    temp_audio_file_path = None
                    try:
                        filename = os.path.basename(file_key)

                        meta_artist = None
                        meta_title = None
                        meta_album = None

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
                                except OSError as e_remove:
                                    logger.warning(
                                        f"Could not remove temp metadata file '{temp_audio_file_path}': {e_remove}")

                        fn_artist_match = re.match(r'^(?:\d+\.\s*)?(.*?)\s+-\s+(.*?)(?:\.mp3|\.wav)$', filename,
                                                   re.IGNORECASE)
                        fn_artist = fn_artist_match.group(1).strip() if fn_artist_match and fn_artist_match.group(
                            1) else ""
                        fn_title = fn_artist_match.group(2).strip() if fn_artist_match and fn_artist_match.group(2) else \
                            os.path.splitext(filename)[0]

                        final_artist = meta_artist if meta_artist is not None else fn_artist
                        final_title = meta_title if meta_title is not None else fn_title
                        final_album = meta_album

                        if final_artist and final_artist.isdigit() and not meta_artist:
                            final_artist = ""

                        final_artist = final_artist if final_artist is not None else ""
                        final_title = final_title if final_title is not None else os.path.splitext(filename)[0]
                        final_album = final_album if final_album is not None else ""

                        logger.debug(
                            f"Consolidated for '{filename}': Artist='{final_artist}', Title='{final_title}', Album='{final_album}'")

                        song_key = (final_artist.lower(), final_title.lower())
                        if song_key in existing_songs:
                            logger.warning(
                                f"Skipping duplicate song (Artist/Title): '{final_artist}' - '{final_title}' from file '{file_key}'")
                            continue

                        mime_type = determine_mime_type(
                            s3_client=s3_client,
                            bucket_name=bucket_name,
                            file_key=file_key,
                            filename=filename,
                            mime_detector=mime_detector,
                            logger=logger,
                            read_bytes=MIME_DETECTION_READ_BYTES
                        )

                        now = datetime.now()
                        song_slug = slugify(final_title)
                        loc_name = generate_loc_name(final_title, final_title, final_title)
                        add_info_value = json.dumps({"source": "Imported"})

                        # First insert the sound fragment record
                        cursor.execute("""
                                INSERT INTO kneobroadcaster__sound_fragments 
                                (author, reg_date, last_mod_user, last_mod_date, source, status, type, 
                                 title, artist, genre, album, loc_name, add_info, slug_name, archived)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                RETURNING id
                            """, (
                            0, now, 0, now, "USERS_UPLOAD", 1, "SONG",
                            final_title, final_artist, "electronic", final_album,
                            json.dumps(loc_name),
                            add_info_value,
                            song_slug, 0
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
                            'DIGITAL_OCEAN', mime_type, song_slug, filename, file_key
                        ))

                        cursor.execute("""
                            INSERT INTO kneobroadcaster__brand_sound_fragments 
                            (brand_id, sound_fragment_id, played_by_brand_count, last_time_played_by_brand)
                            VALUES (%s, %s, %s, %s)
                        """, (brand_id, fragment_id, 0, None))

                        add_default_superuser_permissions(cursor, fragment_id,
                                                          "kneobroadcaster__sound_fragment_readers")

                        existing_files.add(file_key)
                        existing_songs.add(song_key)
                        added_count += 1
                        logger.info(
                            f"Added '{final_title}' by '{final_artist}' (Album: '{final_album}', MIME: {mime_type}) from '{file_key}' to brand '{brand_display_name}'")

                    except Exception as e_file:
                        logger.error(f"Error processing file {file_key} for brand {brand_display_name}: {str(e_file)}")
                    finally:
                        if temp_audio_file_path and os.path.exists(temp_audio_file_path):
                            try:
                                os.remove(temp_audio_file_path)
                            except OSError as e_final_remove:
                                logger.warning(
                                    f"Final cleanup: Could not remove temp metadata file '{temp_audio_file_path}': {e_final_remove}")

                conn.commit()
                logger.info(f"Successfully processed {added_count} new songs for brand {brand_display_name}")

            except Exception as e_brand:
                logger.error(f"Critical error processing brand {brand_display_name}: {str(e_brand)}")
                conn.rollback()

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    logger.info("\nFinished processing all brands")

if __name__ == "__main__":
    generate_sound_fragments()