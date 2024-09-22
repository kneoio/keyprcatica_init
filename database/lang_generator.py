import json
from faker import Faker
from database import get_connection
from util.logging import logger
from cnst.const import LANGUAGES  # Import the centralized language constants

# Translations for each language in three languages: ENG, POR, KAZ
translations = {
    "ENG": {
        "ENG": "English",
        "POR": "Inglês",
        "KAZ": "Ағылшын"
    },
    "POR": {
        "ENG": "Portuguese",
        "POR": "Português",
        "KAZ": "Португал"
    },
    "KAZ": {
        "ENG": "Kazakh",
        "POR": "Cazaque",
        "KAZ": "Қазақ"
    }
}

fake = Faker()

def generate_langs():
    conn = get_connection()
    cursor = conn.cursor()

    # Insert each language into the database
    for code, name in LANGUAGES.items():
        try:
            # Create loc_name reflecting translations in ENG, POR, KAZ
            loc_name = translations[code]  # Use language code (ENG, POR, KAZ) to map to translations

            cursor.execute("""
                INSERT INTO _langs (author, last_mod_user, code, position, loc_name, reg_date, last_mod_date)
                VALUES (%s, %s, %s, %s, %s::jsonb, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                0,  # author set to 0
                0,  # last_mod_user set to 0
                code,  # Language code (ENG, POR, KAZ)
                fake.random_int(min=1, max=100),  # Arbitrary position value
                json.dumps(loc_name)  # Convert the loc_name dict to JSON
            ))
            logger.info(f"Language '{name}' ({code}) inserted with translations.")
        except Exception as e:
            logger.error(f"Error inserting language '{name}' ({code}): {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting languages.")
