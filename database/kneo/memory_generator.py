import json
import random
from datetime import datetime

# Assumes these modules exist in your project structure
from database import get_connection
from util.logging import logger

# The JSON examples for listeners are now "abstract" and stored in a list.
# They are not tied to any specific brand name.
LISTENER_DATA_EXAMPLES = [
    # Example 1
    {
        "Alice": {"location": "Lisbon, Portugal"},
        "Bruno": {"location": "Porto, Portugal"},
        "Clara": {"location": "London, UK"}
    },
    # Example 2
    {
        "David": {"location": "Berlin, Germany"},
        "Eve": {"location": "Paris, France"},
        "Fatima": {"location": "Faro, Portugal"}
    },
    # Example 3
    {
        "Gabe": {"location": "New York, USA"},
        "Heidi": {"location": "Oslo, Norway"},
        "Ivan": {"location": "Warsaw, Poland"}
    },
    # Example 4
    {
        "Jasmine": {"location": "Tokyo, Japan"},
        "Ken": {"location": "Seoul, South Korea"}
    },
    # Example 5
    {
        "Laura": {"location": "Madrid, Spain"},
        "Miguel": {"location": "Rome, Italy"},
        "Nina": {"location": "Amsterdam, Netherlands"}
    }
]

# The audience context examples are also abstract and stored in a list.
AUDIENCE_CONTEXTS_DATA = [
    "Listeners are tuning in during their late-night drive, looking for some chill vibes to end their day.",
    "It's a sunny afternoon, and our audience is kicking back, relaxing, and enjoying the weekend.",
    "The perfect soundtrack for a productive morning at work. Our listeners are locked in and focused.",
    "A high-energy pre-party mix for our audience getting ready for a big night out.",
    "A companion for a quiet, rainy evening indoors with a good book and a warm drink."
]


def populate_brand_memories():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        if conn is None:
            logger.error("Failed to get database connection. Aborting.")
            return

        cursor = conn.cursor()
        now = datetime.now()
        default_user_id = 0

        logger.info("Starting to populate brand memories...")

        # Dynamically finds brand names from your database.
        cursor.execute("SELECT slug_name FROM kneobroadcaster__brands WHERE archived = 0")
        brands = [row[0] for row in cursor.fetchall()]

        if not brands:
            logger.warning("No active brands found in 'kneobroadcaster__brands'. Nothing to populate.")
            return

        logger.info(f"Found {len(brands)} brands to process: {brands}")

        # Loop through each brand found in the database.
        for brand_slug in brands:
            logger.info(f"Processing brand: '{brand_slug}'")

            # --- Generate and Insert LISTENERS Memory ---
            cursor.execute("""
                SELECT 1 FROM kneobroadcaster__memory
                WHERE brand = %s AND memory_type = 'LISTENERS'
            """, (brand_slug,))

            if cursor.fetchone():
                logger.info(f"  - 'LISTENERS' memory already exists for '{brand_slug}'. Skipping.")
            else:
                # Dynamically attach an abstract example to the brand.
                # This randomly picks one of the dictionaries from the LISTENER_DATA_EXAMPLES list.
                listeners_data = random.choice(LISTENER_DATA_EXAMPLES)
                content_json = json.dumps(listeners_data)

                cursor.execute("""
                    INSERT INTO kneobroadcaster__memory
                    (author, reg_date, last_mod_user, last_mod_date, brand, memory_type, content, archived)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    default_user_id, now, default_user_id, now,
                    brand_slug, 'LISTENERS', content_json, False
                ))
                logger.info(f"  + Created 'LISTENERS' memory for '{brand_slug}'.")

            # --- Generate and Insert AUDIENCE_CONTEXT Memory ---
            cursor.execute("""
                SELECT 1 FROM kneobroadcaster__memory
                WHERE brand = %s AND memory_type = 'AUDIENCE_CONTEXT'
            """, (brand_slug,))

            if cursor.fetchone():
                logger.info(f"  - 'AUDIENCE_CONTEXT' memory already exists for '{brand_slug}'. Skipping.")
            else:
                # Dynamically attach an abstract context to the brand.
                context_description = random.choice(AUDIENCE_CONTEXTS_DATA)
                context_data = {"description": context_description}
                content_json = json.dumps(context_data)

                cursor.execute("""
                    INSERT INTO kneobroadcaster__memory
                    (author, reg_date, last_mod_user, last_mod_date, brand, memory_type, content, archived)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    default_user_id, now, default_user_id, now,
                    brand_slug, 'AUDIENCE_CONTEXT', content_json, False
                ))
                logger.info(f"  + Created 'AUDIENCE_CONTEXT' memory for '{brand_slug}'.")

        conn.commit()
        logger.info(f"Successfully processed memories for {len(brands)} brands. Commit successful.")

    except Exception as e:
        logger.error(f"Database connection or major transaction error: {e}")
        if conn:
            conn.rollback()
            logger.warning("Database transaction rolled back due to an error.")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        logger.info("Finished populating brand memories.")


if __name__ == "__main__":
    populate_brand_memories()