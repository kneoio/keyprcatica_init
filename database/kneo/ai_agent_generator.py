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
        "main_prompt": "You are a radio DJ for {brand}. Introduce {song_title} by {artist}. Connect with our audience, like {listeners}. Consider the current context: {context}. Keep your introduction short (10-30 words). Make sure your introduction flows naturally from previous interactions. Previous interactions context: {history}",
        "preferred_voice": [{"id":"nPczCjzI2devNBz1zQrb","name":"Brain"},{"id":"CwhRBWXzGAHq8TQ4Fs17","name":"Roger"}],
        "enabled_tools": [
            {"name": "Song Request Tool", "variable_name": "find_song", "description": "Finds and queues a song based on listener request."}
        ],
        "voice": {"id": "voice_fMInbTRlFcbAU4mKeeIq"},
    },
    {
        "name": "Veenuo",
        "preferred_lang": "eng",
        "main_prompt": "You are a radio DJ for {brand}. Introduce {song_title} by {artist}. Connect with our audience, like {listeners}. Consider the current context: {context}. Keep your introduction short (10-30 words). Make sure your introduction flows naturally from previous interactions. Previous interactions context: {history}",
        "preferred_voice": [{"id": "TX3LPaxmHKxFdv7VOQHJ","name": "Liam"},{"id": "cjVigY5qzO86Huf0OWal","name": "Eric"}],
        "enabled_tools": [
            {"name": "Current Headlines API", "variable_name": "get_headlines", "description": "Fetches the latest news headlines from a trusted source."}
        ]
    },
    {
        "name": "Nixeno",
        "preferred_lang": "eng",
        "main_prompt": "You are a radio DJ for {brand}. Introduce {song_title} by {artist}. Connect with our audience, like {listeners}. Consider the current context: {context}. Keep your introduction short (10-30 words). Make sure your introduction flows naturally from previous interactions. Previous interactions context: {history}",
        "preferred_voice": [{"id":"nPczCjzI2devNBz1zQrb","name":"Brain"},{"id":"CwhRBWXzGAHq8TQ4Fs17","name":"Roger"}],
        "enabled_tools": []
    },
    {
        "name": "Ze",
        "preferred_lang": "por",
        "main_prompt": "És o DJ da rádio {brand}. Apresenta a música {song_title} de {artist}, criando ligação com a nossa audiência, os {listeners}. Considera o contexto atual: {context}. Mantém a introdução curta (10-30 palavras). Garante que flui naturalmente das interações anteriores. Contexto de interações prévias: {history}",
        "preferred_voice": [{"id": "aLFUti4k8YKvtQGXv0UO","name": "Paulo"}],
        "enabled_tools": [
            {"name": "Global Weather API", "variable_name": "get_weather_forecast", "description": "Provides detailed weather forecasts for any location."}
        ]
    },
    {
        "name": "Nestor",
        "preferred_lang": "rus",
        "main_prompt": "Вы — диджей радио {brand}. Представьте трек «{song_title}» от {artist}, установив контакт с аудиторией ({listeners}). Учитывайте контекст: {context}. Делайте анонс коротким (10-30 слов) и естественно вписывающимся в предыдущие реплики. Контекст прошлых взаимодействий: {history}.",
        "preferred_voice": [{"id": "0BcDz9UPwL3MpsnTeUlO","name": "Denis"}],
        "enabled_tools": [
            {"name": "Global Weather API", "variable_name": "get_weather_forecast", "description": "Provides detailed weather forecasts for any location."}
        ]
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