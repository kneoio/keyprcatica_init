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
        if 'Contents' in response:
            return [obj['Key'] for obj in response['Contents']]
        else:
            logger.warning("No files found in the bucket.")
            return []
    except Exception as e:
        logger.error(f"Failed to fetch files from DigitalOcean Spaces: {e}")
        return []

def generate_sound_fragments():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM kneobroadcaster__brands")
    brand_ids = [row[0] for row in cursor.fetchall()]

    if not brand_ids:
        logger.warning("No brands found in the database. Skipping brand-sound fragment binding.")
        return

    files = get_files_from_do_spaces()
    selected_files = random.sample(files, min(10, len(files)))

    for file_key in selected_files:
        try:
            now = datetime.now()

            match = re.match(r'^\d+\.\s+(.*?)\s+-\s+(.*?)\.mp3$', file_key, re.IGNORECASE)
            if match:
                artist = match.group(1).strip()
                title = match.group(2).strip()
            else:
                title = os.path.splitext(file_key)[0]
                artist = fake.name()

            slug_name = slugify(title)
            genre = fake.word()
            album = fake.word()
            loc_name = generate_loc_name(title, title, title)
            add_info = {"source": "DigitalOcean Spaces"}

            # Insert the file key into the do_key field
            do_key = file_key

            cursor.execute("""
                INSERT INTO kneobroadcaster__sound_fragments 
                (author, reg_date, last_mod_user, last_mod_date, source, status, priority, type, title, artist, genre, album, loc_name, add_info, slug_name, do_key, archived)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (
                0, now, 0, now, "DIGITALOCEAN", 1, 1, "SONG",
                title, artist, genre, album, json.dumps(loc_name), json.dumps(add_info), slug_name, do_key, 0
            ))
            fragment_id = cursor.fetchone()[0]

            num_brands_to_associate = random.randint(1, min(3, len(brand_ids)))
            selected_brand_ids = random.sample(brand_ids, num_brands_to_associate)

            for brand_id in selected_brand_ids:
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

            logger.info(f"Sound fragment inserted for file: {file_key}")
        except Exception as e:
            logger.error(f"Error processing file {file_key}: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting sound fragments and binding them to brands.")
