import random

from database import get_connection
from util.logging import logger


def bind_sound_fragments_to_brands():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM kneobroadcaster__brand_sound_fragments")
        logger.info("Deleted all existing bindings from kneobroadcaster__brand_sound_fragments.")

        cursor.execute("SELECT id FROM kneobroadcaster__sound_fragments")
        sound_fragment_ids = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT id FROM kneobroadcaster__brands")
        brand_ids = [row[0] for row in cursor.fetchall()]

        if not sound_fragment_ids:
            logger.warning("No sound fragments found in the database. Skipping binding.")
            return

        if not brand_ids:
            logger.warning("No brands found in the database. Skipping binding.")
            return

        for sound_fragment_id in sound_fragment_ids:
            num_brands_to_associate = random.randint(1, min(3, len(brand_ids)))
            selected_brand_ids = random.sample(brand_ids, num_brands_to_associate)

            for brand_id in selected_brand_ids:
                cursor.execute("""
                    INSERT INTO kneobroadcaster__brand_sound_fragments 
                    (brand_id, sound_fragment_id, played_by_brand_count, last_time_played_by_brand)
                    VALUES (%s, %s, %s, %s)
                """, (brand_id, sound_fragment_id, 0, None))

                logger.info(f"Bound sound fragment {sound_fragment_id} to brand {brand_id}.")

        conn.commit()
        logger.info("Finished binding sound fragments to brands.")

    except Exception as e:
        logger.error(f"Error during binding: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    bind_sound_fragments_to_brands()