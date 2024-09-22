from database import get_connection
from util.logging import logger

def delete_data():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Define the order to delete data to avoid foreign key constraint issues
        tables = [
            "__employees",
            "__departments",
            "__organizations",
            "__positions",
            "__org_categories",
            "__labels",
            "__task_types"
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
