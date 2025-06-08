import json
from datetime import datetime
from faker import Faker
from slugify import slugify
import random

# --- MODIFIED SECTION START ---

# Import VALID_COUNTRY_CODES from your constants file
from cnst.const import generate_loc_name, VALID_COUNTRY_CODES
from database import get_connection
# NOTE: This import is no longer used for country selection and can likely be removed.
from cnst.country_codes import country_codes
from util.logging import logger
from util.permissions import add_default_superuser_permissions

fake = Faker()


def generate_listeners(count=10):
    """Generates listener entries in the database with a valid country code."""
    conn = get_connection()
    cursor = conn.cursor()

    # Fetch all brand IDs first to avoid querying in a loop if no listeners can be created
    cursor.execute("SELECT id FROM kneobroadcaster__brands WHERE archived = 0 ORDER BY RANDOM()")
    brand_rows = cursor.fetchall()
    if not brand_rows:
        logger.error("No active brands found in the database. Cannot create listeners.")
        return
    brand_ids = [row[0] for row in brand_rows]

    # Fetch all user IDs that are not yet listeners
    cursor.execute("""
        SELECT u.id FROM _users u
        LEFT JOIN kneobroadcaster__listeners l ON u.id = l.user_id
        WHERE l.id IS NULL AND u.id > 1
    """)
    user_rows = cursor.fetchall()
    if not user_rows:
        logger.error("No available users to create new listeners for.")
        return
    available_user_ids = [row[0] for row in user_rows]
    random.shuffle(available_user_ids)

    logger.info(f"Attempting to create {count} new listeners...")
    created_count = 0
    for i in range(min(count, len(available_user_ids))):
        try:
            now = datetime.now()
            user_id = available_user_ids[i]
            brand_id = random.choice(brand_ids)  # Assign a random brand

            # Generate listener data
            listener_name = fake.name()
            slug_name = slugify(listener_name)
            nick = fake.user_name()
            loc_name = generate_loc_name(listener_name, listener_name, listener_name)
            nick_name = generate_loc_name(nick, nick, nick)

            # FIX: Use the VALID_COUNTRY_CODES list to get a valid two-letter country code
            country = random.choice(VALID_COUNTRY_CODES)

            # Insert listener
            cursor.execute("""
                INSERT INTO kneobroadcaster__listeners 
                (user_id, author, reg_date, last_mod_user, last_mod_date, country, loc_name, nickname, slug_name, archived)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (
                user_id, 0, now, 0, now,
                country,
                json.dumps(loc_name),
                json.dumps(nick_name),
                slug_name, 0
            ))
            listener_id = cursor.fetchone()[0]

            # Insert listener-brand relationship
            cursor.execute("""
                INSERT INTO kneobroadcaster__listener_brands 
                (listener_id, reg_date, brand_id, rank)
                VALUES (%s, %s, %s, %s)
            """, (
                listener_id, now, brand_id, fake.random_int(min=1, max=100)
            ))

            # Add edit/delete permissions for the user themselves
            cursor.execute("""
                INSERT INTO kneobroadcaster__listener_readers 
                (reader, entity_id, can_edit, can_delete, reading_time)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, listener_id, True, True, now))

            add_default_superuser_permissions(cursor, listener_id, "kneobroadcaster__listener_readers")

            created_count += 1
            logger.info(f"Listener {created_count}/{count} inserted for user_id: {user_id}")

        except Exception as e:
            logger.error(f"Error inserting listener for user {user_id}: {e}")
            conn.rollback()  # Rollback the single failed transaction
            continue  # Continue to the next listener

    conn.commit()  # Commit all successful insertions
    cursor.close()
    conn.close()
    logger.info(f"Finished inserting listeners. Successfully created: {created_count}.")