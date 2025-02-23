import json
from datetime import datetime
from faker import Faker
from slugify import slugify
import random

from cnst.const import generate_loc_name
from database import get_connection
from cnst.country_codes import country_codes
from util.logging import logger
from util.permissions import add_superuser_permissions


fake = Faker()

def generate_listeners(count=10):
    conn = get_connection()
    cursor = conn.cursor()

    for i in range(count):
        try:
            now = datetime.now()

            # Fetch a random user and brand
            cursor.execute(
                "SELECT reader, brand.id "
                "FROM kneobroadcaster__brands brand, kneobroadcaster__brand_readers rls "
                "WHERE brand.id = rls.entity_id AND reader > 1 ORDER BY RANDOM() LIMIT 1"
            )
            row = cursor.fetchone()
            if row is None:
                logger.error("No valid user and brand found for listener creation.")
                continue

            user_id, brand_id = row

            # Check if the user already has a listener
            cursor.execute(
                "SELECT id FROM kneobroadcaster__listeners WHERE user_id = %s LIMIT 1",
                (user_id,)
            )
            if cursor.fetchone() is not None:
                logger.warning(f"User {user_id} already has a listener. Skipping.")
                continue

            # Generate listener data
            listener_name = fake.name()
            slug_name = slugify(listener_name)
            nick = fake.user_name()
            loc_name = generate_loc_name(listener_name, listener_name, listener_name)
            nick_name = generate_loc_name(nick, nick, nick)
            country = random.choice(country_codes)["name"]

            # Insert listener
            cursor.execute("""
                INSERT INTO kneobroadcaster__listeners 
                (user_id, author, reg_date, last_mod_user, last_mod_date, country, loc_name, nickname, slug_name, archived)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (
                user_id,
                0,  # Assuming author is a system user or default value
                now,
                0,  # Assuming last_mod_user is a system user or default value
                now,
                country,
                json.dumps(loc_name),
                json.dumps(nick_name),
                slug_name,
                0  # archived flag
            ))
            listener_id = cursor.fetchone()[0]

            # Insert listener-brand relationship
            cursor.execute("""
                INSERT INTO kneobroadcaster__listener_brands 
                (listener_id, reg_date, brand_id, rank)
                VALUES (%s, %s, %s, %s)
            """, (
                listener_id,
                now,
                brand_id,
                fake.random_int(min=1, max=10)  # Random rank between 1 and 10
            ))

            # Insert listener readers and permissions
            cursor.execute("""
                INSERT INTO kneobroadcaster__listener_readers 
                (reader, entity_id, can_edit, can_delete, reading_time)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                user_id,
                listener_id,
                True,  # can_edit
                True,  # can_delete
                now
            ))

            # Add superuser permissions
            add_superuser_permissions(cursor, listener_id, "kneobroadcaster__listener_readers")

            logger.info(f"Listener {i + 1}/{count} inserted with name: {listener_name}")
        except Exception as e:
            logger.error(f"Error inserting listener {i + 1}: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting listeners.")
