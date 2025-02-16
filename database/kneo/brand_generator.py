import json
from datetime import datetime
from faker import Faker
from slugify import slugify

from cnst.const import generate_loc_name
from database import get_connection
from util.logging import logger
from util.permissions import add_superuser_permissions

fake = Faker()

def generate_brands(count=10):
    conn = get_connection()
    cursor = conn.cursor()

    for i in range(count):
        try:
            now = datetime.now()
            brand_name = fake.company()
            slug_name = slugify(brand_name)
            loc_name = generate_loc_name(brand_name, brand_name, brand_name)

            cursor.execute("""
                INSERT INTO kneobroadcaster__brands 
                (author, reg_date, last_mod_user, last_mod_date, country, primary_lang, loc_name, slug_name, archived)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (
                0, now, 0, now, fake.country_code(), 'eng', json.dumps(loc_name), slug_name, 0
            ))
            brand_id = cursor.fetchone()[0]

            cursor.execute("SELECT id FROM _users ORDER BY RANDOM() LIMIT 1")
            reader = cursor.fetchone()
            if reader:
                cursor.execute("""
                    INSERT INTO kneobroadcaster__brand_readers 
                    (reader, entity_id, can_edit, can_delete, reading_time)
                    VALUES (%s, %s, %s, %s, %s)
                """, (reader[0], brand_id, True, True, now))

            add_superuser_permissions(cursor, brand_id, "kneobroadcaster__brand_readers")

            logger.info(f"Brand {i + 1}/{count} inserted with name: {brand_name}")
        except Exception as e:
            logger.error(f"Error inserting brand {i + 1}: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting brands.")
