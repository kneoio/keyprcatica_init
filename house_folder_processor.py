# house_folder_processor.py

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

# DigitalOcean Spaces configuration
access_key = os.getenv('DO_SPACES_KEY')
secret_key = os.getenv('DO_SPACES_SECRET')
region = os.getenv('DO_SPACES_REGION')
endpoint = os.getenv('DO_SPACES_ENDPOINT')
bucket_name = os.getenv('DO_SPACES_BUCKET')

# Configuration constants
HOUSE_FOLDER_PREFIX = "house/"
MIME_DETECTION_READ_BYTES = 2048
DEFAULT_BRAND_ID = None  # Set this to your default brand ID or leave as None to skip brand association

# Fake data generators for missing metadata
FAKE_HOUSE_ARTISTS = [
    "Deep House Collective", "Midnight Groove", "Bass Foundation", "Rhythm Masters",
    "Electronic Pulse", "Club Vibes", "Dance Floor Heroes", "House Nation",
    "Beat Syndicate", "Groove Machine", "Night Shift", "Sound Wave",
    "Underground Kings", "Mix Masters", "Bass Line", "Synth Squad"
]

FAKE_HOUSE_GENRES = [
    "Deep House", "Tech House", "Progressive House", "Electro House",
    "Minimal House", "Funky House", "Tribal House", "Vocal House"
]


class HouseFolderProcessor:
    def __init__(self):
        self.s3_client = None
        self.mime_detector = None
        self.metadata_parser = None
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize S3 client, MIME detector, and metadata parser"""
        try:
            # Initialize S3 client
            s3_session = boto3.session.Session()
            self.s3_client = s3_session.client(
                's3',
                region_name=region,
                endpoint_url=f"https://{endpoint}",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key
            )

            # Initialize MIME detector
            self.mime_detector = magic.Magic(mime=True)

            # Initialize metadata parser
            self.metadata_parser = AudioMetadataParser(logger)

            logger.info("All clients initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize clients: {e}")
            raise

    def get_house_files_from_do_spaces(self):
        """Get all audio files from the house/ folder in DO Spaces"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=HOUSE_FOLDER_PREFIX
            )

            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    # Skip directories and only include audio files
                    if not key.endswith('/') and key.lower().endswith(('.mp3', '.wav', '.flac', '.m4a')):
                        files.append(key)

            logger.info(f"Found {len(files)} audio files in house/ folder")
            return files

        except Exception as e:
            logger.error(f"Failed to fetch house files: {e}")
            return []

    def extract_metadata_from_file(self, file_key):
        """Extract metadata from audio file, with fallback to fake data"""
        temp_audio_file_path = None
        metadata = {
            'artist': None,
            'title': None,
            'album': None,
            'genre': None
        }

        try:
            filename = os.path.basename(file_key)

            # Try to extract metadata from the actual audio file
            try:
                file_suffix = os.path.splitext(filename)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix) as tmp_f:
                    self.s3_client.download_fileobj(bucket_name, file_key, tmp_f)
                    temp_audio_file_path = tmp_f.name

                parsed_meta = self.metadata_parser.parse_metadata(temp_audio_file_path)
                if parsed_meta:
                    metadata['artist'] = parsed_meta.get("artist")
                    metadata['title'] = parsed_meta.get("title")
                    metadata['album'] = parsed_meta.get("album")
                    metadata['genre'] = parsed_meta.get("genre")

                logger.info(f"Extracted metadata for '{filename}': {metadata}")

            except Exception as e_meta:
                logger.warning(f"Could not extract metadata from '{file_key}': {e_meta}")

            # Try to extract from filename if metadata is missing
            if not metadata['artist'] or not metadata['title']:
                filename_meta = self._extract_from_filename(filename)
                if not metadata['artist']:
                    metadata['artist'] = filename_meta['artist']
                if not metadata['title']:
                    metadata['title'] = filename_meta['title']

            # Fill in missing data with fake data
            if not metadata['artist'] or not metadata['artist'].strip():
                metadata['artist'] = random.choice(FAKE_HOUSE_ARTISTS)
                logger.info(f"Generated fake artist: {metadata['artist']}")

            if not metadata['title'] or not metadata['title'].strip():
                metadata['title'] = self._generate_fake_title()
                logger.info(f"Generated fake title: {metadata['title']}")

            if not metadata['album'] or not metadata['album'].strip():
                metadata['album'] = f"{metadata['artist']} - House Collection"
                logger.info(f"Generated fake album: {metadata['album']}")

            if not metadata['genre'] or not metadata['genre'].strip():
                metadata['genre'] = random.choice(FAKE_HOUSE_GENRES)
                logger.info(f"Generated fake genre: {metadata['genre']}")

            return metadata

        except Exception as e:
            logger.error(f"Error processing metadata for {file_key}: {e}")
            # Return completely fake metadata as fallback
            return {
                'artist': random.choice(FAKE_HOUSE_ARTISTS),
                'title': self._generate_fake_title(),
                'album': f"{random.choice(FAKE_HOUSE_ARTISTS)} - House Collection",
                'genre': random.choice(FAKE_HOUSE_GENRES)
            }
        finally:
            if temp_audio_file_path and os.path.exists(temp_audio_file_path):
                try:
                    os.remove(temp_audio_file_path)
                except OSError as e_remove:
                    logger.warning(f"Could not remove temp file '{temp_audio_file_path}': {e_remove}")

    def _extract_from_filename(self, filename):
        """Extract artist and title from filename"""
        # Remove file extension
        name_without_ext = os.path.splitext(filename)[0]

        # Try various patterns
        patterns = [
            r'^(?:\d+[\.\s]*)?(.+?)\s*[-–—]\s*(.+)$',  # Artist - Title
            r'^(.+?)\s*[-–—]\s*(.+)$',  # Artist - Title (without number)
            r'^(.+?)_(.+)$',  # Artist_Title
            r'^(.+?)\s+(.+)$'  # Artist Title (space separated)
        ]

        for pattern in patterns:
            match = re.match(pattern, name_without_ext, re.IGNORECASE)
            if match:
                artist = match.group(1).strip()
                title = match.group(2).strip()

                # Skip if artist is just a number
                if artist.isdigit():
                    continue

                return {'artist': artist, 'title': title}

        # If no pattern matches, use filename as title
        return {'artist': '', 'title': name_without_ext}

    def _generate_fake_title(self):
        """Generate a fake house music title"""
        prefixes = ["Deep", "Underground", "Midnight", "Electric", "Groove", "Bass", "Night", "Club"]
        suffixes = ["Vibes", "Beat", "Pulse", "Flow", "Drop", "Wave", "Mix", "Track", "Sound"]

        return f"{random.choice(prefixes)} {random.choice(suffixes)}"

    def _upload_to_spaces_with_acl(self, file_path, destination_key):
        """Upload file to DO Spaces with public-read ACL"""
        try:
            self.s3_client.upload_file(
                file_path,
                bucket_name,
                destination_key,
                ExtraArgs={'ACL': 'public-read'}
            )
            logger.info(f"Successfully uploaded {destination_key} with public-read ACL")
            return True
        except Exception as e:
            logger.error(f"Failed to upload {file_path} to DO Spaces: {e}")
            return False

    def get_existing_sound_fragments(self, cursor):
        """Get existing sound fragments to avoid duplicates"""
        existing_songs = set()
        existing_files = set()

        try:
            # Get existing songs by artist/title combination
            cursor.execute(
                "SELECT LOWER(COALESCE(artist, '')), LOWER(COALESCE(title, '')) FROM kneobroadcaster__sound_fragments")
            for row in cursor.fetchall():
                existing_songs.add((row[0], row[1]))

            # Get existing file keys
            cursor.execute("SELECT file_key FROM _files WHERE parent_table = 'kneobroadcaster__sound_fragments'")
            for row in cursor.fetchall():
                existing_files.add(row[0])

            logger.info(f"Found {len(existing_songs)} existing songs and {len(existing_files)} existing files")

        except Exception as e:
            logger.error(f"Error fetching existing data: {e}")

        return existing_songs, existing_files

    def get_brand_uuid(self, cursor, brand_id):
        """Get brand UUID from brand_id"""
        try:
            if brand_id is None:
                return None

            cursor.execute("SELECT id FROM kneobroadcaster__brands WHERE id = %s", (brand_id,))
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                logger.warning(f"Brand ID {brand_id} not found, will skip brand association")
                return None
        except Exception as e:
            logger.error(f"Error fetching brand UUID: {e}")
            return None

    def process_house_files(self, brand_id=None):
        """Main processing function"""
        if brand_id is None:
            brand_id = DEFAULT_BRAND_ID

        conn = get_connection()
        cursor = conn.cursor()

        processed_count = 0
        added_count = 0

        try:
            # Get brand UUID if brand_id is provided
            brand_uuid = self.get_brand_uuid(cursor, brand_id) if brand_id else None
            if brand_id and not brand_uuid:
                logger.warning(f"Could not find brand with ID {brand_id}, continuing without brand association")

            # Get existing data to avoid duplicates
            existing_songs, existing_files = self.get_existing_sound_fragments(cursor)

            # Get all house files
            house_files = self.get_house_files_from_do_spaces()

            if not house_files:
                logger.info("No house files found to process")
                return

            # Filter out already processed files
            new_files = [f for f in house_files if f not in existing_files]
            logger.info(f"Found {len(new_files)} new files to process")

            for file_key in new_files:
                processed_count += 1
                logger.info(f"Processing file {processed_count}/{len(new_files)}: {file_key}")

                try:
                    # Extract metadata
                    metadata = self.extract_metadata_from_file(file_key)

                    # Check for duplicate songs
                    song_key = (
                        metadata['artist'].lower() if metadata['artist'] else '',
                        metadata['title'].lower() if metadata['title'] else ''
                    )

                    if song_key in existing_songs:
                        logger.warning(f"Skipping duplicate song: '{metadata['artist']}' - '{metadata['title']}'")
                        continue

                    # Determine MIME type
                    filename = os.path.basename(file_key)
                    mime_type = determine_mime_type(
                        s3_client=self.s3_client,
                        bucket_name=bucket_name,
                        file_key=file_key,
                        filename=filename,
                        mime_detector=self.mime_detector,
                        logger=logger,
                        read_bytes=MIME_DETECTION_READ_BYTES
                    )

                    # Create sound fragment record
                    now = datetime.now()
                    song_slug = slugify(metadata['title']) if metadata['title'] else slugify(filename)
                    loc_name = generate_loc_name(metadata['title'], metadata['title'], metadata['title'])
                    add_info_value = json.dumps({"source": "House Folder Import", "original_path": file_key})

                    cursor.execute("""
                        INSERT INTO kneobroadcaster__sound_fragments 
                        (author, reg_date, last_mod_user, last_mod_date, source, status, type, 
                         title, artist, genre, album, loc_name, add_info, slug_name, archived)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        0, now, 0, now, "USERS_UPLOAD", 1, "SONG",
                        metadata['title'], metadata['artist'], metadata['genre'], metadata['album'],
                        json.dumps(loc_name),
                        add_info_value,
                        song_slug, 0
                    ))
                    fragment_id = cursor.fetchone()[0]

                    # Create file record
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

                    # Link to brand if specified and UUID was found
                    if brand_uuid:
                        cursor.execute("""
                            INSERT INTO kneobroadcaster__brand_sound_fragments 
                            (brand_id, sound_fragment_id, played_by_brand_count, last_time_played_by_brand)
                            VALUES (%s, %s, %s, %s)
                        """, (brand_uuid, fragment_id, 0, None))
                        logger.info(f"Linked fragment {fragment_id} to brand {brand_uuid}")

                    # Add default permissions
                    add_default_superuser_permissions(cursor, fragment_id, "kneobroadcaster__sound_fragment_readers")

                    # Set ACL on the file in DO Spaces (make it publicly readable)
                    try:
                        self.s3_client.put_object_acl(
                            Bucket=bucket_name,
                            Key=file_key,
                            ACL='public-read'
                        )
                        logger.info(f"Set public-read ACL for {file_key}")
                    except Exception as e_acl:
                        logger.warning(f"Could not set ACL for {file_key}: {e_acl}")

                    # Commit this record
                    conn.commit()

                    # Update tracking sets
                    existing_files.add(file_key)
                    existing_songs.add(song_key)
                    added_count += 1

                    logger.info(
                        f"Successfully added: '{metadata['title']}' by '{metadata['artist']}' (ID: {fragment_id})")

                except Exception as e_file:
                    logger.error(f"Error processing file {file_key}: {e_file}")
                    conn.rollback()
                    continue

            # Final commit for any remaining changes
            conn.commit()
            logger.info(f"Processing complete! Processed: {processed_count}, Added: {added_count}")

        except KeyboardInterrupt:
            logger.info("Processing interrupted by user")
            conn.rollback()
            raise
        except Exception as e:
            logger.error(f"Critical error during processing: {e}")
            conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def run(self, brand_id=None):
        """Run the house folder processor"""
        logger.info("Starting house folder processing...")
        logger.info(f"Target folder: {HOUSE_FOLDER_PREFIX}")
        logger.info(f"Brand ID: {brand_id or DEFAULT_BRAND_ID}")

        try:
            self.process_house_files(brand_id)
            logger.info("House folder processing completed successfully!")
        except Exception as e:
            logger.error(f"House folder processing failed: {e}")
            raise


if __name__ == "__main__":
    # Configuration - you can also look up brand by slug_name
    target_brand_id = None  # Set to specific brand ID or leave None to skip brand association

    # Alternative: Look up brand by slug_name
    # conn = get_connection()
    # cursor = conn.cursor()
    # cursor.execute("SELECT id FROM kneobroadcaster__brands WHERE slug_name = %s", ('your-brand-slug',))
    # result = cursor.fetchone()
    # target_brand_id = result[0] if result else None
    # cursor.close()
    # conn.close()

    processor = HouseFolderProcessor()

    try:
        processor.run(brand_id=target_brand_id)
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
    except Exception as e_main:
        logger.critical(f"Main process failed: {e_main}", exc_info=True)
    finally:
        logger.info("House folder processor script finished.")