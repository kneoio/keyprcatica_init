from database import get_connection
from util.logging import logger
from cnst.const import generate_loc_name  # Import the helper function
import json

# Hardcoded task types
task_types = [
    {"identifier": "dev", "loc_name": generate_loc_name("Development", "Desenvolvimento", "Даму")},
    {"identifier": "testing", "loc_name": generate_loc_name("Testing", "Testes", "Тестілеу")},
    {"identifier": "documenting", "loc_name": generate_loc_name("Documenting", "Documentação", "Құжаттау")},
    {"identifier": "bugfix", "loc_name": generate_loc_name("Bugfix", "Correção de Erros", "Қателерді түзету")}
]


def generate_task_types():
    conn = get_connection()
    cursor = conn.cursor()

    for task_type in task_types:
        try:
            loc_name_json = json.dumps(task_type["loc_name"])

            cursor.execute("""
                INSERT INTO __task_types (author, last_mod_user, identifier, loc_name)
                VALUES (%s, %s, %s, %s)
                """, (
                0,  # author set to 0
                0,  # last_mod_user set to 0
                task_type["identifier"],
                loc_name_json  # loc_name as JSON
            ))
            logger.info(f"Task Type '{task_type['identifier']}' inserted.")
        except Exception as e:
            logger.error(f"Error inserting task type '{task_type['identifier']}': {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting task types.")
