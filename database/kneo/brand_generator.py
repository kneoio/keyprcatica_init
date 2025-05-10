import json
from datetime import datetime
from faker import Faker
from slugify import slugify
import random
import colorsys

from cnst.const import generate_loc_name
from database import get_connection
from cnst.country_codes import country_codes
from util.logging import logger
from util.permissions import add_superuser_permissions

fake = Faker()

# List of static brand names that will always be inserted first
STATIC_BRAND_NAMES = [
    "nunoscope",
    "aidazoo",
    "nitroglycerin",
    "fock-fock",
    "klentara",
    "enacone",
]


def generate_brand_color(brand_name):
    """Generate a consistent color based on brand name hash"""
    # Create a hash from the brand name
    name_hash = hash(brand_name)

    # Use the hash to generate consistent HSV values
    h = (name_hash % 360) / 360.0  # Hue (0-1)
    s = 0.7 + ((name_hash % 30) / 100.0)  # Saturation (0.7-1.0)
    v = 0.5 + ((name_hash % 40) / 100.0)  # Value (0.5-0.9)

    # Convert HSV to RGB
    r, g, b = colorsys.hsv_to_rgb(h, s, v)

    # Convert to hex color code
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def generate_brands(count=10):
    conn = get_connection()
    cursor = conn.cursor()

    # Calculate how many random brands we need after inserting static ones
    static_count = min(len(STATIC_BRAND_NAMES), count)
    remaining_count = max(count - static_count, 0)

    # First insert static brands (up to the requested count)
    for i, brand_name in enumerate(STATIC_BRAND_NAMES[:static_count]):
        try:
            now = datetime.now()
            slug_name = slugify(brand_name)
            loc_name = generate_loc_name(brand_name, brand_name, brand_name)
            country = random.choice(country_codes)["name"]
            color = generate_brand_color(brand_name)  # Generate brand color

            cursor.execute("""
                INSERT INTO kneobroadcaster__brands 
                (author, reg_date, last_mod_user, last_mod_date, country, primary_lang, 
                 loc_name, slug_name, archived, color, schedule, ai_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (
                0, now, 0, now, country, 'eng',
                json.dumps(loc_name), slug_name, 0, color,
                json.dumps({}), json.dumps({})  # New fields with empty JSON objects
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

            logger.info(f"Static brand {i + 1}/{static_count} inserted with name: {brand_name}")
            conn.commit()  # Commit after each successful brand insertion
        except Exception as e:
            logger.error(f"Error inserting static brand {i + 1}: {e}")
            conn.rollback()  # Rollback on error to prevent transaction abortion
            continue  # Continue to next brand instead of failing completely

    # Then insert remaining random brands if needed
    for i in range(remaining_count):
        try:
            now = datetime.now()
            brand_name = fake.company()
            slug_name = slugify(brand_name)
            loc_name = generate_loc_name(brand_name, brand_name, brand_name)
            country = random.choice(country_codes)["name"]
            color = generate_brand_color(brand_name)  # Generate brand color

            cursor.execute("""
                INSERT INTO kneobroadcaster__brands 
                (author, reg_date, last_mod_user, last_mod_date, country, primary_lang, 
                 loc_name, slug_name, archived, color, schedule, ai_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (
                0, now, 0, now, country, 'eng',
                json.dumps(loc_name), slug_name, 0, color,
                json.dumps({}), json.dumps({})  # New fields with empty JSON objects
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

            logger.info(f"Random brand {i + 1}/{remaining_count} inserted with name: {brand_name}")
            conn.commit()  # Commit after each successful brand insertion
        except Exception as e:
            logger.error(f"Error inserting random brand {i + 1}: {e}")
            conn.rollback()  # Rollback on error to prevent transaction abortion
            continue  # Continue to next brand instead of failing completely

    cursor.close()
    conn.close()
    logger.info(f"Finished inserting brands. Total: {count} (Static: {static_count}, Random: {remaining_count})")