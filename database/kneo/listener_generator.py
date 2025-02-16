import json
from datetime import datetime
from faker import Faker
from slugify import slugify
import random

from cnst.const import generate_loc_name
from database import get_connection
from database.country_codes import country_codes
from util.logging import logger
from util.permissions import add_superuser_permissions


fake = Faker()

def generate_listeners(count=10):
    conn = get_connection()
    cursor = conn.cursor()

    for i in range(count):
        try:
            now = datetime.now()
            cursor.execute(
                "SELECT reader, brand.id "
                "FROM kneobroadcaster__brands brand, kneobroadcaster__brand_readers rls "
                "WHERE brand.id = rls.entity_id and reader > 1 ORDER BY RANDOM() LIMIT 1"
            )
            row = cursor.fetchone()
            if row is None:
                logger.error("No valid user and brand found for listener creation.")
                continue

            user_id, brand_id = row

            listener_name = fake.name()
            slug_name = slugify(listener_name)
            nick = fake.user_name()
            loc_name = generate_loc_name(listener_name, listener_name, listener_name)
            nick_name = generate_loc_name(nick, nick, nick)

            country = random.choice(country_codes)["name"]

            cursor.execute("""
                INSERT INTO kneobroadcaster__listeners 
                (user_id, author, reg_date, last_mod_user, last_mod_date, country, loc_name, nick_name, slug_name, archived)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (
                user_id,
                0,
                now,
                0,
                now,
                country,
                json.dumps(loc_name),
                json.dumps(nick_name),
                slug_name,
                0
            ))
            listener_id = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO kneobroadcaster__listeners_brands 
                (id, reg_date, brand_id, rank)
                VALUES (%s, %s, %s, %s)
            """, (
                listener_id,
                now,
                brand_id,
                fake.random_int(min=1, max=10)
            ))

            cursor.execute("""
                INSERT INTO kneobroadcaster__listener_readers 
                (reader, entity_id, can_edit, can_delete, reading_time)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                user_id,
                listener_id,
                True,
                True,
                now
            ))

            add_superuser_permissions(cursor, listener_id, "kneobroadcaster__listener_readers")

            logger.info(f"Listener {i + 1}/{count} inserted with name: {listener_name}")
        except Exception as e:
            logger.error(f"Error inserting listener {i + 1}: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting listeners.")
