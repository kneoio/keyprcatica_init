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

STATIC_BRAND_CONFIGS = [
    {
        "name": "skyscope",
        "color": "#1E88E5",
        "country": "PT",
        "time_zone": "Europe/Lisbon",
        "managing_mode": "AI_AGENT",
        "description": "Ambient electronic and downtempo music for focus and relaxation. Features atmospheric soundscapes, chillout beats, and modern instrumental compositions perfect for work or study sessions."
    },
    {
        "name": "aizoo",
        "color": "#FF6B35",
        "country": "JP",
        "time_zone": "Asia/Tokyo",
        "managing_mode": "AI_AGENT",
        "description": "Cutting-edge J-pop, electronic dance music, and experimental beats. Showcasing the latest trends in Japanese music culture with high-energy tracks and innovative sound design."
    },
    {
        "name": "nitroglycerin",
        "color": "#DC143C",
        "country": "DE",
        "time_zone": "Europe/Berlin",
        "managing_mode": "AI_AGENT",
        "description": "High-octane rock, metal, and punk music that hits hard. From classic heavy metal anthems to modern hardcore punk, delivering explosive energy 24/7."
    },
    {
        "name": "bratan",
        "color": "#4CAF50",
        "country": "KZ",
        "time_zone": "Asia/Almaty",
        "managing_mode": "AI_AGENT",
        "description": "Traditional Slavic folk music mixed with modern electronic elements. Features balalaika-infused beats, Russian chanson, and contemporary interpretations of Eastern European melodies."
    },
    {
        "name": "bit2bit",
        "color": "#9C27B0",
        "country": "GB",
        "time_zone": "Europe/London",
        "managing_mode": "AI_AGENT",
        "description": "Nostalgic chiptune and 8-bit music celebrating retro gaming culture. From classic arcade soundtracks to modern chip music artists, perfect for gamers and digital nostalgia enthusiasts."
    },
    {
        "name": "mood387",
        "color": "#FF9800",
        "country": "PT",
        "time_zone": "Europe/Lisbon",
        "managing_mode": "AI_AGENT",
        "description": "Smooth bossa nova, Brazilian jazz, and Latin rhythms that set the perfect mood. Features both classic MPB legends and contemporary Brazilian artists with soulful melodies and tropical vibes."
    }
]


def generate_unique_ai_name():
    """Generate a unique AI agent name"""
    syllables1 = ["Zor", "Xyl", "Glo", "Vee", "Nix", "Kael", "Crym", "Plaz"]
    syllables2 = ["tek", "nex", "lar", "qon", "vex", "tron", "mar", "flux"]
    return random.choice(syllables1) + random.choice(syllables2) + str(random.randint(100, 999))


def generate_brands():
    """
    Generates brand entries in the database using static configurations,
    assigning a pre-existing or newly created AI agent to each.
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

        for i, brand_config in enumerate(STATIC_BRAND_CONFIGS):
            try:
                now = datetime.now()
                brand_name = brand_config["name"]
                slug_name = slugify(brand_name)
                loc_name = generate_loc_name(brand_name, brand_name, brand_name)

                # Use hardcoded values from configuration
                country = brand_config["country"]
                color = brand_config["color"]
                time_zone = brand_config["time_zone"]
                managing_mode = brand_config["managing_mode"]
                description = brand_config["description"]

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
                     loc_name, slug_name, archived, color, schedule, ai_agent_id, managing_mode, time_zone, description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (
                    0, now, 0, now, country,
                    json.dumps(loc_name),
                    slug_name,
                    0,  # archived = False
                    color,
                    json.dumps({}), ai_agent_id, managing_mode, time_zone, description
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
                    f"Brand {i + 1}/{len(STATIC_BRAND_CONFIGS)} inserted: {brand_name} ({country}, {time_zone})")
                logger.info(f"  Color: {color}, AI Agent: {ai_agent_name_log}")
                logger.info(f"  Description: {description[:50]}...")
                conn.commit()

            except Exception as e:
                logger.error(f"Error inserting brand {i + 1} ({brand_config['name']}): {e}")
                conn.rollback()
                continue

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
        logger.info(f"Finished inserting {len(STATIC_BRAND_CONFIGS)} static brands.")


if __name__ == '__main__':
    logger.info("Starting enhanced brand generation script...")
    generate_brands()
    logger.info("Brand generation script finished.")