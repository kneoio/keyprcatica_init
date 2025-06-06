import json
from datetime import datetime
from slugify import slugify
import random
import colorsys

# Assuming these modules exist in your project structure
from cnst.const import generate_loc_name
from database import get_connection
from cnst.country_codes import country_codes
from util.logging import logger
from util.permissions import add_default_superuser_permissions

STATIC_BRAND_NAMES = [
    "skyscope",
    "aizoo",
    "nitroglycerin",
    "bratan",
    "bit2bit",
    "mood387"
]


def generate_brand_color(brand_name):
    """Generates a consistent color based on the brand name."""
    name_hash = hash(brand_name)
    h = (name_hash % 360) / 360.0
    s = 0.7 + ((name_hash % 30) / 100.0)
    v = 0.5 + ((name_hash % 40) / 100.0)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def generate_unique_ai_name():
    """Generates a random, unique-looking AI name as a fallback."""
    syllables1 = ["Zor", "Xyl", "Glo", "Vee", "Nix", "Kael", "Crym", "Plaz"]
    syllables2 = ["tek", "nex", "lar", "qon", "vex", "tron", "mar", "flux"]
    return random.choice(syllables1) + random.choice(syllables2) + str(random.randint(100, 999))


def generate_brands():
    """
    Generates brand entries in the database, assigning a pre-existing AI agent to each.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Fetch all available AI agents from the database first
        cursor.execute("SELECT name, preferred_lang, preferred_voice FROM kneobroadcaster__ai_agents WHERE archived = FALSE")
        ai_agents = cursor.fetchall()

        if not ai_agents:
            logger.warning("No AI agents found in the database. Will fall back to generating new AI data.")

        for i, brand_name in enumerate(STATIC_BRAND_NAMES):
            try:
                now = datetime.now()
                slug_name = slugify(brand_name)
                loc_name = generate_loc_name(brand_name, brand_name, brand_name)
                country = random.choice(country_codes)["name"] if country_codes else "Unknown"
                color = generate_brand_color(brand_name)
                ai_agent_data = {}

                if ai_agents:
                    # Randomly select a pre-existing AI agent
                    selected_agent = random.choice(ai_agents)
                    ai_agent_data = {
                        "name": selected_agent[0],
                        "language": selected_agent[1],
                        "preferredVoice": selected_agent[2]
                    }
                    ai_agent_name_log = selected_agent[0]
                else:
                    # Fallback to the original method if no agents are in the DB
                    fallback_name = generate_unique_ai_name()
                    ai_agent_data = {
                        "name": fallback_name,
                        "language": "eng",
                        "preferredVoice": ["nPczCjzI2devNBz1zQrb"]
                    }
                    ai_agent_name_log = f"{fallback_name} (generated)"


                cursor.execute("""
                    INSERT INTO kneobroadcaster__brands
                    (author, reg_date, last_mod_user, last_mod_date, country, primary_lang,
                     loc_name, slug_name, archived, color, schedule, ai_agent)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (
                    0, now, 0, now, country, 'eng',
                    json.dumps(loc_name), slug_name, False, color,
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

                logger.info(f"Brand {i + 1}/{len(STATIC_BRAND_NAMES)} inserted: {brand_name}, AI Agent: {ai_agent_name_log}")
                conn.commit()

            except Exception as e:
                logger.error(f"Error inserting brand {i + 1} ({brand_name}): {e}")
                conn.rollback()
                continue

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
        logger.info(f"Finished inserting {len(STATIC_BRAND_NAMES)} static brands.")


if __name__ == '__main__':
    logger.info("Starting brand generation script...")
    generate_brands()
    logger.info("Brand generation script finished.")