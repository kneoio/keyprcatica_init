import json
from datetime import datetime
from slugify import slugify
import random
import colorsys

from cnst.const import generate_loc_name, VALID_COUNTRY_CODES
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

# The helper functions (generate_brand_color, generate_unique_ai_name) remain the same.
def generate_brand_color(brand_name):
    # ... (no changes here)
    name_hash = hash(brand_name)
    h = (name_hash % 360) / 360.0
    s = 0.7 + ((name_hash % 30) / 100.0)
    v = 0.5 + ((name_hash % 40) / 100.0)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))

def generate_unique_ai_name():
    # ... (no changes here)
    syllables1 = ["Zor", "Xyl", "Glo", "Vee", "Nix", "Kael", "Crym", "Plaz"]
    syllables2 = ["tek", "nex", "lar", "qon", "vex", "tron", "mar", "flux"]
    return random.choice(syllables1) + random.choice(syllables2) + str(random.randint(100, 999))


def generate_brands():
    """
    Generates brand entries in the database, assigning a pre-existing or newly created
    AI agent to each, in compliance with the updated database schema.
    """
    conn = get_connection()
    cursor = conn.cursor()
    ai_agents = []
    created_fallback_agent_id = None
    created_fallback_agent_name = None

    try:
        cursor.execute("SELECT id, name FROM kneobroadcaster__ai_agents WHERE archived = FALSE")
        ai_agents = cursor.fetchall()

        if not ai_agents:
            logger.warning("No AI agents found. A new fallback AI agent will be created and used.")
            try:
                now = datetime.now()
                fallback_name = generate_unique_ai_name()
                cursor.execute("""
                    INSERT INTO kneobroadcaster__ai_agents
                    (author, reg_date, last_mod_user, last_mod_date, archived, name, preferred_lang, preferred_voice)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (
                    0, now, 0, now, False, fallback_name, 'en',
                    json.dumps(["nPczCjzI2devNBz1zQrb"])
                ))
                created_fallback_agent_id = cursor.fetchone()[0]
                created_fallback_agent_name = f"{fallback_name} (generated)"
                conn.commit()
                logger.info(f"Successfully created fallback AI agent with ID: {created_fallback_agent_id}")
            except Exception as e:
                logger.error(f"Fatal: Failed to create a fallback AI agent: {e}. Aborting script.")
                conn.rollback()
                return

        for i, brand_name in enumerate(STATIC_BRAND_NAMES):
            try:
                now = datetime.now()
                slug_name = slugify(brand_name)
                loc_name = generate_loc_name(brand_name, brand_name, brand_name)
                country = random.choice(VALID_COUNTRY_CODES) if VALID_COUNTRY_CODES else 'PT'
                color = generate_brand_color(brand_name)
                ai_agent_id = None
                ai_agent_name_log = None

                if ai_agents:
                    selected_agent = random.choice(ai_agents)
                    ai_agent_id = selected_agent[0]
                    ai_agent_name_log = selected_agent[1]
                elif created_fallback_agent_id:
                    ai_agent_id = created_fallback_agent_id
                    ai_agent_name_log = created_fallback_agent_name
                else:
                    logger.error(f"Cannot find or create an AI agent for brand {brand_name}. Skipping.")
                    continue

                cursor.execute("""
                    INSERT INTO kneobroadcaster__brands
                    (author, reg_date, last_mod_user, last_mod_date, country, 
                     loc_name, slug_name, archived, color, schedule, ai_agent_id, managing_mode, time_zone)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (
                    0, now, 0, now, country,
                    json.dumps(loc_name),
                    slug_name,
                    0, # <<< THE FIX IS HERE: Changed `False` to `0`.
                    color,
                    json.dumps({}), ai_agent_id, 'AI_AGENT', 'Europe/Lisbon'
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

                logger.info(f"Brand {i + 1}/{len(STATIC_BRAND_NAMES)} inserted: {brand_name}, Linked AI Agent: {ai_agent_name_log}")
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