import json
from database import get_connection
from util.logging import logger
from cnst.const import generate_loc_name

labels = [
    {
        "identifier": "rock",
        "color": "#FF5733",
        "category": "genre",
        "loc_name": generate_loc_name("Rock", "Rock", "Рок")
    },
    {
        "identifier": "pop",
        "color": "#FFC300",
        "category": "genre",
        "loc_name": generate_loc_name("Pop", "Pop", "Поп")
    },
    {
        "identifier": "jazz",
        "color": "#900C3F",
        "category": "genre",
        "loc_name": generate_loc_name("Jazz", "Jazz", "Джаз")
    },
    {
        "identifier": "electronic",
        "color": "#581845",
        "category": "genre",
        "loc_name": generate_loc_name("Electronic", "Electrónica", "Электронды")
    },
    {
        "identifier": "classical",
        "color": "#1D8348",
        "category": "genre",
        "loc_name": generate_loc_name("Classical", "Clássica", "Классикалық")
    },
    {
        "identifier": "hiphop",
        "color": "#2E86C1",
        "category": "genre",
        "loc_name": generate_loc_name("Hip Hop", "Hip Hop", "Хип-хоп")
    },
    {
        "identifier": "reggae",
        "color": "#27AE60",
        "category": "genre",
        "loc_name": generate_loc_name("Reggae", "Reggae", "Регги")
    }
]

def generate_labels():
    conn = get_connection()
    cursor = conn.cursor()

    for label in labels:
        try:
            loc_name_json = json.dumps(label["loc_name"])
            cursor.execute("""
                INSERT INTO __labels (author, last_mod_user, identifier, color, category, loc_name)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                0,
                0,
                label["identifier"],
                label["color"],
                label["category"],
                loc_name_json
            ))
            logger.info(f"Label '{label['identifier']}' inserted with translations.")
        except Exception as e:
            logger.error(f"Error inserting label '{label['identifier']}': {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting labels.")
