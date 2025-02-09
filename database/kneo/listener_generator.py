import json
from datetime import datetime
from faker import Faker
from slugify import slugify

from cnst.const import generate_loc_name
from database import get_connection
from util.logging import logger

fake = Faker()

def generate_listeners(count=10):
    conn = get_connection()
    cursor = conn.cursor()

    for i in range(count):
        try:
            now = datetime.now()
            cursor.execute("SELECT id FROM _users ORDER BY RANDOM() LIMIT 1")
            user_id = cursor.fetchone()[0]

            listener_name = fake.name()
            slug_name = slugify(listener_name)
            nick = fake.user_name()
            loc_name = generate_loc_name(listener_name, listener_name, listener_name)
            nick_name = generate_loc_name(nick, nick, nick)

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
                fake.country_code(),
                json.dumps(loc_name),
                json.dumps(nick_name),
                slug_name,
                0
            ))
            listener_id = cursor.fetchone()[0]

            cursor.execute("SELECT id FROM kneobroadcaster__brands ORDER BY RANDOM() LIMIT 1")
            brand_id = cursor.fetchone()[0]
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
            logger.info(f"Listener {i + 1}/{count} inserted with name: {listener_name}")
        except Exception as e:
            logger.error(f"Error inserting listener {i + 1}: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting listeners.")
