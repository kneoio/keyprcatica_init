import json
from database import get_connection
from util.logging import logger
from cnst.const import generate_loc_name

labels = [
    {
        "identifier": "suno",
        "color": "#FF8C00",
        "category": "platform",
        "loc_name": generate_loc_name("Suno", "Suno", "Suno")
    },
    {
        "identifier": "jingle",
        "color": "#4682B4",
        "category": "audio_type",
        "loc_name": generate_loc_name("Jingle", "Jingle", "Джингл")
    },
    {
        "identifier": "speech",
        "color": "#32CD32",
        "category": "audio_type",
        "loc_name": generate_loc_name("Speech", "Discurso", "Речь")
    },
    {
        "identifier": "jamendo",
        "color": "#9370DB",
        "category": "platform",
        "loc_name": generate_loc_name("Jamendo", "Jamendo", "Jamendo")
    },
    {
        "identifier": "censored",
        "color": "#DC143C",
        "category": "content_status",
        "loc_name": generate_loc_name("Censored", "Censurado", "Под цензурой")
    }
]


def generate_labels():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        if conn is None:
            logger.error("Failed to get database connection for __labels. Aborting.")
            return
        cursor = conn.cursor()

        logger.info("Starting to insert new labels into __labels table...")

        for label_data in labels:
            try:
                loc_name_json = json.dumps(label_data["loc_name"])

                cursor.execute("""
                    INSERT INTO __labels (author, last_mod_user, identifier, color, category, loc_name)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    0,
                    0,
                    label_data["identifier"],
                    label_data["color"],
                    label_data["category"],
                    loc_name_json
                ))
                logger.info(f"Label '{label_data['identifier']}' inserted into __labels.")
            except Exception as e:
                logger.error(f"Error inserting label '{label_data['identifier']}' into __labels: {e}")

        conn.commit()
        logger.info(f"Finished inserting {len(labels)} new labels into __labels.")

    except Exception as e:
        logger.error(f"Major error during __labels generation: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        logger.info("Finished __labels generation process.")


if __name__ == "__main__":
    generate_labels_new()