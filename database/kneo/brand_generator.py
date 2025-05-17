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
from util.permissions import add_default_superuser_permissions

fake = Faker()

STATIC_BRAND_NAMES = [
    "nunoscope",
    "aidazoo",
    "nitroglycerin",
    "fock-fock",
    "klentara",
    "enacone",
]


def generate_brand_color(brand_name):
    name_hash = hash(brand_name)

    h = (name_hash % 360) / 360.0
    s = 0.7 + ((name_hash % 30) / 100.0)  # Saturation (0.7-1.0)
    v = 0.5 + ((name_hash % 40) / 100.0)  # Value (0.5-0.9)

    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def generate_unique_ai_name():
    syllables1 = ["Zor", "Xyl", "Glo", "Vee", "Nix", "Kael", "Crym", "Plaz"]
    syllables2 = ["tek", "nex", "lar", "qon", "vex", "tron", "mar", "flux"]
    name = random.choice(syllables1) + random.choice(syllables2) + str(random.randint(100, 999))
    return name


def generate_brands(count=10):
    conn = get_connection()
    cursor = conn.cursor()

    static_count = min(len(STATIC_BRAND_NAMES), count)
    remaining_count = max(count - static_count, 0)

    for i, brand_name in enumerate(STATIC_BRAND_NAMES[:static_count]):
        try:
            now = datetime.now()
            slug_name = slugify(brand_name)
            loc_name = generate_loc_name(brand_name, brand_name, brand_name)
            country_list = country_codes
            if not country_list:
                country = "Unknown"
            else:
                country = random.choice(country_list)["name"]
            color = generate_brand_color(brand_name)

            ai_agent_name = generate_unique_ai_name()
            ai_agent_data = {
                "name": ai_agent_name,
                "language": "ENG",
                "preferredVoice": ["nPczCjzI2devNBz1zQrb"]
            }

            cursor.execute("""
                INSERT INTO kneobroadcaster__brands 
                (author, reg_date, last_mod_user, last_mod_date, country, primary_lang, 
                 loc_name, slug_name, archived, color, schedule, ai_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (
                0, now, 0, now, country, 'eng',
                json.dumps(loc_name), slug_name, 0, color,
                json.dumps({}), json.dumps(ai_agent_data)
            ))
            brand_id = cursor.fetchone()[0]

            cursor.execute("SELECT id FROM _users ORDER BY RANDOM() LIMIT 1")
            reader_row = cursor.fetchone()
            if reader_row:
                reader_id = reader_row[0]
                cursor.execute("""
                    INSERT INTO kneobroadcaster__brand_readers 
                    (reader, entity_id, can_edit, can_delete, reading_time)
                    VALUES (%s, %s, %s, %s, %s)
                """, (reader_id, brand_id, True, True, now))

            add_default_superuser_permissions(cursor, brand_id, "kneobroadcaster__brand_readers")

            logger.info(
                f"Static brand {i + 1}/{static_count} inserted with name: {brand_name}, AI Agent: {ai_agent_name}")
            conn.commit()
        except Exception as e:
            logger.error(f"Error inserting static brand {i + 1} ({brand_name}): {e}")
            conn.rollback()
            continue

    for i in range(remaining_count):
        try:
            now = datetime.now()
            brand_name = fake.company()
            slug_name = slugify(brand_name)
            loc_name = generate_loc_name(brand_name, brand_name, brand_name)
            country_list = country_codes
            if not country_list:
                country = "Unknown"
            else:
                country = random.choice(country_list)["name"]
            color = generate_brand_color(brand_name)

            ai_agent_name = generate_unique_ai_name()
            ai_agent_data = {
                "name": ai_agent_name,
                "language": "ENG",
                "preferredVoice": ["nPczCjzI2devNBz1zQrb"]
            }

            cursor.execute("""
                INSERT INTO kneobroadcaster__brands 
                (author, reg_date, last_mod_user, last_mod_date, country, primary_lang, 
                 loc_name, slug_name, archived, color, schedule, ai_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (
                0, now, 0, now, country, 'eng',
                json.dumps(loc_name), slug_name, 0, color,
                json.dumps({}), json.dumps(ai_agent_data)
            ))
            brand_id = cursor.fetchone()[0]

            cursor.execute("SELECT id FROM _users ORDER BY RANDOM() LIMIT 1")
            reader_row = cursor.fetchone()
            if reader_row:
                reader_id = reader_row[0]
                cursor.execute("""
                    INSERT INTO kneobroadcaster__brand_readers 
                    (reader, entity_id, can_edit, can_delete, reading_time)
                    VALUES (%s, %s, %s, %s, %s)
                """, (reader_id, brand_id, True, True, now))

            add_superuser_permissions(cursor, brand_id, "kneobroadcaster__brand_readers")

            logger.info(
                f"Random brand {i + 1}/{remaining_count} inserted with name: {brand_name}, AI Agent: {ai_agent_name}")  # MODIFIED LOG
            conn.commit()
        except Exception as e:
            logger.error(f"Error inserting random brand {i + 1} ({brand_name}): {e}")
            conn.rollback()
            continue

    cursor.close()
    conn.close()
    logger.info(f"Finished inserting brands. Total: {count} (Static: {static_count}, Random: {remaining_count})")


if __name__ == '__main__':
    logger.info("Starting brand generation script...")
    generate_brands(count=7)
    logger.info("Brand generation script finished.")
