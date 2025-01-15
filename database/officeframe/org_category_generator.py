import json

from database import get_connection
from util.logging import logger
from cnst.const import generate_loc_name  # Import the helper function

# Hardcoded organization categories
org_categories = [
    {"identifier": "holding", "loc_name": generate_loc_name("Holding Company", "Empresa Holding", "Холдинг компаниясы")},
    {"identifier": "ltd", "loc_name": generate_loc_name("Limited Company", "Empresa Limitada", "Жауапкершілігі шектеулі серіктестік")},
    {"identifier": "state_agency", "loc_name": generate_loc_name("State Agency", "Agência Estatal", "Мемлекеттік агенттік")},
    {"identifier": "fund", "loc_name": generate_loc_name("Investment Fund", "Fundo de Investimento", "Инвестициялық қор")}
]

def generate_org_categories():
    conn = get_connection()
    cursor = conn.cursor()

    for org_category in org_categories:
        try:
            cursor.execute("""
                INSERT INTO __org_categories (author, last_mod_user, identifier, loc_name)
                VALUES (%s, %s, %s, %s)
                """, (
                0,  # author set to 0
                0,  # last_mod_user set to 0
                org_category["identifier"],
                json.dumps(org_category["loc_name"])  # loc_name as JSON
            ))
            logger.info(f"Org Category '{org_category['identifier']}' inserted.")
        except Exception as e:
            logger.error(f"Error inserting org category '{org_category['identifier']}': {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting org categories.")