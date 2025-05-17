import os
from datetime import datetime
from dotenv import load_dotenv
from database import get_connection
from util.logging import logger

load_dotenv()

MAIN_TABLES = [
    'kneobroadcaster__sound_fragments',
]

ADMIN_USER_ID = int(os.environ['ADMIN_USER_ID'])


def get_reader_table_name(main_table):
    base_name = main_table[:-1] if main_table.endswith('s') else main_table
    return f"{base_name}_readers"


def table_exists(cursor, table_name):
    try:
        cursor.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s);",
                       (table_name.lower(),))
        return cursor.fetchone()[0]
    except Exception as e:
        logger.error(f"Error checking table: {e}")
        return False


def clean_and_set_admin_permissions():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM _users WHERE id = %s", (ADMIN_USER_ID,))
        if not cursor.fetchone():
            logger.error(f"User {ADMIN_USER_ID} doesn't exist")
            return

        total_cleaned = 0
        permissions_set = 0

        for main_table in MAIN_TABLES:
            reader_table = get_reader_table_name(main_table)

            if not table_exists(cursor, reader_table):
                continue

            try:
                cursor.execute(f"DELETE FROM {reader_table}")
                total_cleaned += cursor.rowcount
            except Exception as e:
                logger.error(f"Clean failed: {e}")
                conn.rollback()
                continue

            try:
                cursor.execute(f"SELECT id FROM {main_table}")
                now = datetime.now()
                for entity_id in cursor.fetchall():
                    cursor.execute(f"""
                        INSERT INTO {reader_table} 
                        (reader, entity_id, can_edit, can_delete, reading_time)
                        VALUES (%s, %s, %s, %s, %s);
                    """, (ADMIN_USER_ID, entity_id[0], True, True, now))
                    permissions_set += 1
            except Exception as e:
                logger.error(f"Insert failed: {e}")
                conn.rollback()
                continue

        conn.commit()
        logger.info(f"Cleaned {total_cleaned} records, set {permissions_set} permissions")

    except Exception as e:
        logger.error(f"Process failed: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    clean_and_set_admin_permissions()