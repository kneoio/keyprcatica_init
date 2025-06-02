import json
import os
import random
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Set, Tuple
import boto3  # Add this import

import magic
import psycopg2
from dotenv import load_dotenv
from slugify import slugify

from database import get_connection
from util.audio_metadata_parser import AudioMetadataParser
from util.logging import logger
from util.permissions import add_default_superuser_permissions


# Load environment variables
load_dotenv()

# Configuration
SONGS_PER_BRAND = 50  # Maximum number of songs to add per brand
SUPPORTED_EXTENSIONS = {'.mp3', '.wav'}
BATCH_SIZE = 10  # Number of files to process in one batch


class LocalSoundFragmentGenerator:
    def __init__(self):
        self.music_path = os.getenv('LOCAL_MUSIC_PATH')
        if not self.music_path:
            raise ValueError("LOCAL_MUSIC_PATH not set in .env file")

        self.music_path = Path(self.music_path)
        if not self.music_path.exists():
            raise ValueError(f"Music directory does not exist: {self.music_path}")

        self.mime_detector = magic.Magic(mime=True)
        self.metadata_parser = AudioMetadataParser(logger)
        self.conn = self._get_database_connection()

    def _get_database_connection(self) -> psycopg2.extensions.connection:
        """Establish database connection using environment variables"""
        try:
            return psycopg2.connect(
                dbname=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT')
            )
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def _get_audio_files(self) -> List[Path]:
        """Recursively collect all supported audio files from the music directory"""
        audio_files = []
        for ext in SUPPORTED_EXTENSIONS:
            audio_files.extend(self.music_path.rglob(f"*{ext}"))
        return audio_files

    def _get_existing_songs(self) -> Set[Tuple[str, str]]:
        """Get existing artist-title combinations from database"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT LOWER(artist), LOWER(title) FROM kneobroadcaster__sound_fragments")
        existing = {(row[0], row[1]) for row in cursor.fetchall()}
        cursor.close()
        return existing

    def _get_brands(self) -> List[Dict]:
        """Get all active brands from database"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, slug_name 
            FROM kneobroadcaster__brands 
            WHERE archived = 0
        """)
        brands = [{'id': row[0], 'slug': row[1]} for row in cursor.fetchall()]
        cursor.close()
        return brands

    def _process_audio_file(self, file_path: Path, brand_id: str) -> Optional[bool]:
        """Process a single audio file and add it to the database"""
        cursor = self.conn.cursor()
        try:
            # Get file metadata
            metadata = self.metadata_parser.parse_metadata(str(file_path))

            # Determine artist and title
            artist = metadata.get('artist', '') or file_path.stem.split(' - ')[0] if ' - ' in file_path.stem else ''
            title = metadata.get('title', '') or file_path.stem.split(' - ')[1] if ' - ' in file_path.stem else file_path.stem
            album = metadata.get('album', '')

            # Clean and encode strings
            try:
                artist = artist.encode('utf-8', errors='ignore').decode('utf-8') if artist else ''
                title = title.encode('utf-8', errors='ignore').decode('utf-8') if title else ''
                album = album.encode('utf-8', errors='ignore').decode('utf-8') if album else ''
            except Exception as e:
                logger.warning(f"Error cleaning strings for {file_path.name}: {e}")
                artist = str(artist) if artist else ''
                title = str(title) if title else file_path.name
                album = str(album) if album else ''

            # Generate slug
            slug_name = slugify(title)

            # Get MIME type
            mime_type = self.mime_detector.from_file(str(file_path))

            # Current timestamp
            now = datetime.now()

            # Generate the DO Spaces key
            file_key = f"music/{slug_name}{file_path.suffix.lower()}"

            # Upload to DO Spaces
            if not self._upload_to_spaces(file_path, file_key):
                logger.error(f"Skipping {file_path} due to upload failure")
                return False

            # Insert sound fragment record
            cursor.execute("""
                INSERT INTO kneobroadcaster__sound_fragments 
                (author, reg_date, last_mod_user, last_mod_date, source, status, type,
                 title, artist, genre, album, loc_name, add_info, slug_name, archived)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                0, now, 0, now, "USERS_UPLOAD", 1, "SONG",
                title, artist, "electronic", album,
                json.dumps({"en": title, "ru": title, "uk": title}),
                json.dumps({"source": "Local Import"}),
                slug_name, 0
            ))
            fragment_id = cursor.fetchone()[0]

            # Insert file record
            cursor.execute("""
                INSERT INTO _files 
                (reg_date, last_mod_date, parent_table, parent_id, archived,
                storage_type, mime_type, slug_name, file_original_name, file_key)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                now, now,
                'kneobroadcaster__sound_fragments', fragment_id, 0,
                'DIGITAL_OCEAN', mime_type, slug_name, file_path.name, file_key
            ))

            # Create brand association
            cursor.execute("""
                INSERT INTO kneobroadcaster__brand_sound_fragments 
                (brand_id, sound_fragment_id, played_by_brand_count, last_time_played_by_brand)
                VALUES (%s, %s, %s, %s)
            """, (brand_id, fragment_id, 0, None))

            # Add permissions
            add_default_superuser_permissions(cursor, fragment_id, "kneobroadcaster__sound_fragment_readers")

            self.conn.commit()
            logger.info(f"Successfully added '{title}' by '{artist}' from {file_path.name}")
            return True

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error processing file {file_path}: {e}")
            return False
        finally:
            cursor.close()

    def generate(self):
        """Main generation process"""
        try:
            # Get all audio files
            audio_files = self._get_audio_files()
            if not audio_files:
                logger.warning(f"No audio files found in {self.music_path}")
                return

            # Get existing songs to avoid duplicates
            existing_songs = self._get_existing_songs()

            # Get active brands
            brands = self._get_brands()
            if not brands:
                logger.warning("No active brands found in database")
                return

            # Process each brand
            for brand in brands:
                logger.info(f"\nProcessing brand: {brand['slug']}")

                # Check how many songs the brand already has
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM kneobroadcaster__brand_sound_fragments 
                    WHERE brand_id = %s
                """, (brand['id'],))
                existing_count = cursor.fetchone()[0]
                cursor.close()

                songs_to_add = max(0, SONGS_PER_BRAND - existing_count)
                if songs_to_add == 0:
                    logger.info(f"Brand {brand['slug']} already has enough songs ({existing_count})")
                    continue

                # Randomly select files to process
                selected_files = random.sample(audio_files, min(songs_to_add, len(audio_files)))

                # Process selected files
                added_count = 0
                for file_path in selected_files:
                    if self._process_audio_file(file_path, brand['id']):
                        added_count += 1

                logger.info(f"Added {added_count} songs to brand {brand['slug']}")

        except Exception as e:
            logger.error(f"Generation process failed: {e}")
        finally:
            self.conn.close()

    def _get_database_connection(self):
        """Establish database connection"""
        return get_connection()

    def _upload_to_spaces(self, file_path: Path, destination_key: str) -> bool:
        """Upload file to DO Spaces"""
        try:
            s3_session = boto3.session.Session()
            s3_client = s3_session.client(
                's3', 
                region_name=os.getenv('DO_SPACES_REGION'),
                endpoint_url=f"https://{os.getenv('DO_SPACES_ENDPOINT')}",
                aws_access_key_id=os.getenv('DO_SPACES_KEY'),
                aws_secret_access_key=os.getenv('DO_SPACES_SECRET')
            )
            s3_client.upload_file(str(file_path), os.getenv('DO_SPACES_BUCKET'), destination_key)
            return True
        except Exception as e:
            logger.error(f"Failed to upload {file_path} to DO Spaces: {e}")
            return False


if __name__ == "__main__":
    logger.info("Starting local sound fragment generation...")
    try:
        generator = LocalSoundFragmentGenerator()
        generator.generate()
    except Exception as e:
        logger.error(f"Failed to initialize or run generator: {e}")
    logger.info("Local sound fragment generation completed.")