import json
from datetime import datetime
from slugify import slugify
import random

from cnst.const import generate_loc_name
from database import get_connection
from util.logging import logger
from util.permissions import add_default_superuser_permissions

STATIC_BRAND_CONFIGS = [
    {
        "name": "sexta",
        "color": "#1E88E5",
        "country": "PT",
        "time_zone": "Europe/Lisbon",
        "managing_mode": "MIX",
        "description": "Ambient electronic and downtempo music for focus and relaxation. Features atmospheric soundscapes, chillout beats, and modern instrumental compositions perfect for work or study sessions."
    },
    {
        "name": "aizoo",
        "color": "#FF6B35",
        "country": "JP",
        "time_zone": "Asia/Tokyo",
        "managing_mode": "MIX",
        "description": "Cutting-edge J-pop, electronic dance music, and experimental beats. Showcasing the latest trends in Japanese music culture with high-energy tracks and innovative sound design."
    },
    {
        "name": "nitroglycerin",
        "color": "#DC143C",
        "country": "DE",
        "time_zone": "Europe/Berlin",
        "managing_mode": "ITSELF",
        "description": "High-octane rock, metal, and punk music that hits hard. From classic heavy metal anthems to modern hardcore punk, delivering explosive energy 24/7."
    },
    {
        "name": "bratan",
        "color": "#4CAF50",
        "country": "KZ",
        "time_zone": "Asia/Almaty",
        "managing_mode": "MIX",
        "description": "Deep house, funk, disco, and electronic dance music with groovy basslines. Features underground house beats, classic funk rhythms, and modern disco-influenced tracks that keep the dance floor moving."
    },
    {
        "name": "the-radiola",
        "color": "#9C27B0",
        "country": "GB",
        "time_zone": "Europe/London",
        "managing_mode": "MIX",
        "description": "We're your go-to for all things retro, from the swingin' jazz of the '20s to the soulful R&B of the '60s, and the classic rock anthems of the '70s. Perfect for anyone who loves the warm, authentic vibes of bygone eras."
    },
    {
        "name": "labirints",
        "color": "#FF9800",
        "country": "LV",
        "time_zone": "Europe/Riga",
        "managing_mode": "MIX",
        "description": "Dark industrial, experimental electronic, and intelligent dance music (IDM). Features harsh mechanical beats, complex rhythmic patterns, and avant-garde electronic compositions for discerning listeners."
    }
]

COUNTRY_LANGUAGE_MAP = {
    "PT": ["pt", "en"],  # Portuguese, fallback to English
    "JP": ["ja", "en"],  # Japanese, fallback to English
    "DE": ["de", "en"],  # German, fallback to English
    "KZ": ["kk", "ru", "en"],  # Kazakh, fallback to Russian, then English
    "GB": ["en"],  # English
    "LV": ["lv", "en"],  # Latvian, fallback to English
    "RU": ["ru", "en"],  # Russian, fallback to English
    "US": ["en"],  # English
    "FR": ["fr", "en"],  # French, fallback to English
    "ES": ["es", "en"],  # Spanish, fallback to English
    "IT": ["it", "en"],  # Italian, fallback to English
    "CN": ["zh", "en"],  # Chinese, fallback to English
    "BR": ["pt", "en"],  # Portuguese (Brazil), fallback to English
}


def find_best_ai_agent(ai_agents, country):
    if not ai_agents:
        return None

    preferred_languages = COUNTRY_LANGUAGE_MAP.get(country, ["en"])

    for preferred_lang in preferred_languages:
        matching_agents = [agent for agent in ai_agents if agent[2] == preferred_lang]
        if matching_agents:
            logger.info(
                f"Found {len(matching_agents)} agent(s) with preferred language '{preferred_lang}' for country '{country}'")
            return random.choice(matching_agents)

    logger.info(f"No language-specific agent found for country '{country}', selecting random agent")
    return random.choice(ai_agents)


def generate_brands():
    conn = get_connection()
    cursor = conn.cursor()
    ai_agents = []

    try:
        cursor.execute("SELECT id, name, preferred_lang FROM kneobroadcaster__ai_agents WHERE archived = 0")
        ai_agents = cursor.fetchall()

        if not ai_agents:
            logger.error("No AI agents found in database. Please run the AI agent generator first.")
            return

        logger.info(f"Found {len(ai_agents)} available AI agents")

        for i, brand_config in enumerate(STATIC_BRAND_CONFIGS):
            try:
                now = datetime.now()
                brand_name = brand_config["name"]
                slug_name = slugify(brand_name)
                loc_name = generate_loc_name(brand_name, brand_name, brand_name)

                country = brand_config["country"]
                color = brand_config["color"]
                time_zone = brand_config["time_zone"]
                managing_mode = brand_config["managing_mode"]
                description = brand_config["description"]

                # --- MODIFICATION START ---
                ai_agent_id = None  # Initialize to None
                ai_agent_name = "N/A"
                ai_agent_lang = "N/A"

                if managing_mode == "AI_AGENT":
                    selected_agent = find_best_ai_agent(ai_agents, country)
                    if not selected_agent:
                        logger.error(f"Cannot find a suitable AI agent for brand {brand_name} (managing_mode=AI_AGENT). Skipping.")
                        continue
                    ai_agent_id = selected_agent[0]
                    ai_agent_name = selected_agent[1]
                    ai_agent_lang = selected_agent[2]
                else:
                    logger.info(f"Brand {brand_name} is managed by ITSELF. AI agent will not be bound.")

                cursor.execute("""
                    INSERT INTO kneobroadcaster__brands
                    (author, reg_date, last_mod_user, last_mod_date, country,
                     loc_name, slug_name, archived, color, schedule, ai_agent_id, managing_mode, time_zone, description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (
                    0, now, 0, now, country,
                    json.dumps(loc_name),
                    slug_name,
                    0,
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
                logger.info(f"  Color: {color}, AI Agent: {ai_agent_name} (lang: {ai_agent_lang})")
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