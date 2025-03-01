from database import get_connection
from util.logging import logger

def delete_data():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        tables = [
            #"kneobroadcaster__listeners_brands",
            #"kneobroadcaster__listener_readers",
            #"kneobroadcaster__listeners",
            #"kneobroadcaster__brand_readers",
            #"kneobroadcaster__brands",
            #"__labels",
            "kneobroadcaster__sound_fragment_readers",
            "kneobroadcaster__sound_fragment_files",
            "kneobroadcaster__sound_fragments"
        ]

        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
            logger.info(f"Deleted all records from {table}")

        conn.commit()
    except Exception as e:
        logger.error(f"Error deleting data: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    delete_data()
