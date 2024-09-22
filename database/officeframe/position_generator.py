from database import get_connection
from util.logging import logger
from cnst.const import generate_loc_name  # Import the helper function
import json

# Hardcoded positions
positions = [
    {"identifier": "CEO", "loc_name": generate_loc_name("CEO", "CEO", "CEO")},
    {"identifier": "project_manager",
     "loc_name": generate_loc_name("Project Manager", "Gestor de Projetos", "Жоба менеджері")},
    {"identifier": "tester", "loc_name": generate_loc_name("Tester", "Testador", "Тестірлеуші")},
    {"identifier": "middle_developer",
     "loc_name": generate_loc_name("Middle Developer", "Desenvolvedor Intermediário", "Орташа әзірлеуші")},
    {"identifier": "senior_developer",
     "loc_name": generate_loc_name("Senior Developer", "Desenvolvedor Sénior", "Аға әзірлеуші")}
]


def generate_positions():
    conn = get_connection()
    cursor = conn.cursor()

    for position in positions:
        try:
            loc_name_json = json.dumps(position["loc_name"])

            cursor.execute("""
                INSERT INTO __positions (author, last_mod_user, identifier, loc_name)
                VALUES (%s, %s, %s, %s)
                """, (
                0,  # author set to 0
                0,  # last_mod_user set to 0
                position["identifier"],
                loc_name_json  # loc_name as JSON
            ))
            logger.info(f"Position '{position['identifier']}' inserted.")
        except Exception as e:
            logger.error(f"Error inserting position '{position['identifier']}': {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting positions.")
