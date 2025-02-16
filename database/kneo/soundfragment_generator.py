import os
import re
import json
import random
from datetime import datetime
from faker import Faker
from slugify import slugify

from cnst.const import generate_loc_name
from database import get_connection
from util.logging import logger
from util.permissions import add_superuser_permissions

fake = Faker()

def generate_sound_fragments():
    folder = r"C:/Users/justa/tmp/hits_of70_80_90"
    conn = get_connection()
    cursor = conn.cursor()

    mp3_files = [f for f in os.listdir(folder) if f.lower().endswith(".mp3")]
    selected_files = random.sample(mp3_files, min(5, len(mp3_files)))

    for filename in selected_files:
        try:
            file_path = os.path.join(folder, filename)
            with open(file_path, "rb") as f:
                file_data = f.read()
            now = datetime.now()

            match = re.match(r'^\d+\.\s+(.*?)\s+-\s+(.*?)\.mp3$', filename, re.IGNORECASE)
            if match:
                artist = match.group(1).strip()
                title = match.group(2).strip()
            else:
                title = os.path.splitext(filename)[0]
                artist = fake.name()

            slug_name = slugify(title)
            genre = fake.word()
            album = fake.word()
            loc_name = generate_loc_name(title, title, title)
            add_info = {"file_size": len(file_data)}

            cursor.execute("""
                INSERT INTO kneobroadcaster__sound_fragments 
                (author, reg_date, last_mod_user, last_mod_date, source, status, priority, played, file_uri, local_path, type, title, slug_name, artist, genre, album, loc_name, add_info, archived)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (
                0, now, 0, now, "local", 1, 1, 0, "file://" + filename, file_path, "mp3",
                title, slug_name, artist, genre, album, json.dumps(loc_name), json.dumps(add_info), 0
            ))
            fragment_id = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO kneobroadcaster__sound_fragments_files 
                (entity_id, original_name, mime_type, size, file_data, version)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (fragment_id, filename, "audio/mpeg", len(file_data), file_data, 1))

            cursor.execute("SELECT id FROM __labels ORDER BY RANDOM() LIMIT 1")
            label = cursor.fetchone()
            if label:
                cursor.execute("""
                    INSERT INTO kneobroadcaster__sound_fragments_labels 
                    (id, label_id)
                    VALUES (%s, %s)
                """, (fragment_id, label[0]))

            cursor.execute("SELECT id FROM _users ORDER BY RANDOM() LIMIT 1")
            reader = cursor.fetchone()
            if reader:
                cursor.execute("""
                    INSERT INTO kneobroadcaster__sound_fragments_readers 
                    (reader, entity_id, can_edit, can_delete, reading_time)
                    VALUES (%s, %s, %s, %s, %s)
                """, (reader[0], fragment_id, False, False, now))

            add_superuser_permissions(cursor, fragment_id, "kneobroadcaster__sound_fragments_readers")

            logger.info(f"Sound fragment inserted for file: {filename}")
        except Exception as e:
            logger.error(f"Error processing file {filename}: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting sound fragments.")
