import json
import random
from datetime import datetime

# Assumes these modules exist in your project structure
from database import get_connection
from util.logging import logger

AI_AGENT_DATA_EXAMPLES = [
    {
        "name": "Glo",
        "preferred_lang": "eng",
        "main_prompt": "You are DJ Nova, an upbeat and energetic host for a dance music radio station. Keep the vibe positive and exciting.",
        "preferred_voice": ["alloy", "shimmer"],
        "enabled_tools": [
            {"name": "Song Request Tool", "variable_name": "find_song", "description": "Finds and queues a song based on listener request."}
        ],
        "voice": {"id": "voice_fMInbTRlFcbAU4mKeeIq"},
    },
    {
        "name": "Veenuo",
        "preferred_lang": "eng",
        "main_prompt": "You are Alex, a professional and authoritative news anchor. Deliver the news clearly, concisely, and with impartiality.",
        "preferred_voice": ["echo", "onyx"],
        "enabled_tools": [
            {"name": "Current Headlines API", "variable_name": "get_headlines", "description": "Fetches the latest news headlines from a trusted source."}
        ],
        "voice": {"id": "voice_21m00Tcm4TlvDq8ikWAM"},
    },
    {
        "name": "Nixeno",
        "preferred_lang": "por",
        "main_prompt": "É a Sofia, uma narradora de contos infantis com uma voz calma e cativante. As suas histórias devem ser mágicas e adequadas para crianças.",
        "preferred_voice": ["nova", "fable"],
        "enabled_tools": [],
        "voice": {"id": "voice_LcfcDJNUP1GQjkzn1xUU"},
    },
    {
        "name": "Clentara",
        "preferred_lang": "eng",
        "main_prompt": "You are Wendy, a friendly and helpful weather bot. Provide weather forecasts in a cheerful and easy-to-understand manner.",
        "preferred_voice": ["shimmer"],
        "enabled_tools": [
            {"name": "Global Weather API", "variable_name": "get_weather_forecast", "description": "Provides detailed weather forecasts for any location."}
        ],
        "voice": {"id": "voice_pMsXgVXv3BLzUgSXRplE"},
    },
]


def populate_ai_agents():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now()
        default_user_id = 0

        logger.info("Starting to populate AI agents...")

        for agent_data in AI_AGENT_DATA_EXAMPLES:
            agent_name = agent_data["name"]
            logger.info(f"Processing agent: '{agent_name}'")

            cursor.execute("""
                SELECT 1 FROM kneobroadcaster__ai_agents WHERE name = %s
            """, (agent_name,))

            if cursor.fetchone():
                logger.info(f"  - Agent '{agent_name}' already exists. Skipping.")
                continue

            preferred_voice_json = json.dumps(agent_data["preferred_voice"])
            enabled_tools_json = json.dumps(agent_data["enabled_tools"])
            voice_json = json.dumps(agent_data["voice"])

            cursor.execute("""
                INSERT INTO kneobroadcaster__ai_agents
                (author, reg_date, last_mod_user, last_mod_date, name, preferred_lang, main_prompt, preferred_voice, enabled_tools, voice, archived)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                default_user_id, now, default_user_id, now,
                agent_data["name"],
                agent_data["preferred_lang"],
                agent_data["main_prompt"],
                preferred_voice_json,
                enabled_tools_json,
                voice_json,
                False
            ))
            logger.info(f"  + Created agent '{agent_name}'.")

        conn.commit()
        logger.info(f"Successfully processed {len(AI_AGENT_DATA_EXAMPLES)} potential agents. Commit successful.")

    except Exception as e:
        logger.error(f"A database error occurred: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
        logger.info("Finished populating AI agents.")


if __name__ == "__main__":
    populate_ai_agents()