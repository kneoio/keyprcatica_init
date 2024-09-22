from database import get_connection
from util.logging import logger
from cnst.const import generate_loc_name  # Import the helper function
import json

# Hardcoded departments data
departments = [
    {"identifier": "advertising", "loc_name": generate_loc_name("Advertising", "Publicidade", "Жарнама")},
    {"identifier": "marketing", "loc_name": generate_loc_name("Marketing", "Marketing", "Маркетинг")},
    {"identifier": "development", "loc_name": generate_loc_name("Development", "Desenvolvimento", "Даму")},
    {"identifier": "hr", "loc_name": generate_loc_name("HR", "Recursos Humanos", "Адам ресурстары")},
    {"identifier": "accounting", "loc_name": generate_loc_name("Accounting", "Contabilidade", "Бухгалтерлік есеп")}
]


def generate_departments():
    conn = get_connection()
    cursor = conn.cursor()

    for department in departments:
        try:
            # Select a random type_id from task types
            cursor.execute("SELECT id FROM __task_types ORDER BY RANDOM() LIMIT 1")
            type_id = cursor.fetchone()[0]

            # Select a random organization_id from organizations
            cursor.execute("SELECT id FROM __organizations ORDER BY RANDOM() LIMIT 1")
            organization_id = cursor.fetchone()[0]

            loc_name_json = json.dumps(department["loc_name"])

            cursor.execute("""
                INSERT INTO __departments (author, last_mod_user, identifier, type_id, organization_id, loc_name)
                VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                0,  # author set to 0
                0,  # last_mod_user set to 0
                department["identifier"],
                type_id,  # type_id from task types
                organization_id,  # organization_id from organizations
                loc_name_json  # loc_name as JSON
            ))
            logger.info(f"Department '{department['identifier']}' inserted.")
        except Exception as e:
            logger.error(f"Error inserting department '{department['identifier']}': {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting departments.")
