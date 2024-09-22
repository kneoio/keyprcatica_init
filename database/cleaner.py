from database import get_connection
from util.logging import logger

def clean_tables():
    conn = get_connection()
    cursor = conn.cursor()

    tables = ["_user_roles", "_user_modules", "_roles", "_langs", "_modules", "_users"]

    try:
        for table in tables:
            cursor.execute(f"DELETE FROM {table} CASCADE;")
            logger.info(f"Cleaned table: {table}")

        conn.commit()
        logger.info("All tables cleaned successfully.")
    except Exception as e:
        logger.error(f"Error while cleaning tables: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
        logger.info("Database connection closed.")
