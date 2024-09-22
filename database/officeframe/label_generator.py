from database import get_connection
from util.logging import logger
from cnst.const import generate_loc_name  # Import the helper function
import json

# Hardcoded label data with HEX colors using the generate_loc_name helper
labels = [
    {
        "identifier": "urgent",
        "color": "#FF0000",  # Red
        "category": "priority",
        "loc_name": generate_loc_name("Urgent", "Urgente", "Шұғыл")
    },
    {
        "identifier": "bug",
        "color": "#FFFF00",  # Yellow
        "category": "issue",
        "loc_name": generate_loc_name("Bug", "Erro", "Қате")
    },
    {
        "identifier": "postponed",
        "color": "#0000FF",  # Blue
        "category": "status",
        "loc_name": generate_loc_name("Postponed", "Adiado", "Кейінге қалдырылды")
    },
    {
        "identifier": "fixes",
        "color": "#00FF00",  # Green
        "category": "action",
        "loc_name": generate_loc_name("Fixes", "Correções", "Түзетулер")
    },
    {
        "identifier": "javascript",
        "color": "#800080",  # Purple
        "category": "technology",
        "loc_name": generate_loc_name("JavaScript", "JavaScript", "JavaScript")
    },
    {
        "identifier": "java",
        "color": "#FFA500",  # Orange
        "category": "technology",
        "loc_name": generate_loc_name("Java", "Java", "Java")
    },
    {
        "identifier": "ops",
        "color": "#808080",  # Gray
        "category": "team",
        "loc_name": generate_loc_name("Ops", "Ops", "Ops")
    }
]


def generate_labels():
    conn = get_connection()
    cursor = conn.cursor()

    # Insert predefined labels into the database
    for label in labels:
        try:
            # Convert loc_name to JSON for insertion
            loc_name_json = json.dumps(label["loc_name"])

            cursor.execute("""
                INSERT INTO __labels (author, last_mod_user, identifier, color, category, loc_name)
                VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                0,  # author set to 0
                0,  # last_mod_user set to 0
                label["identifier"],
                label["color"],  # HEX color code
                label["category"],
                loc_name_json  # loc_name as JSON with translations
            ))
            logger.info(f"Label '{label['identifier']}' inserted with translations.")
        except Exception as e:
            logger.error(f"Error inserting label '{label['identifier']}': {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting labels.")
