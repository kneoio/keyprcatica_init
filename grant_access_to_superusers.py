from datetime import datetime
from database import get_connection
from util.logging import logger

MAIN_TABLES = [
    'kneobroadcaster__sound_fragments',
]

READ_ONLY_USER_IDS = [
]

def get_reader_table_name(main_table):
    base_name = main_table[:-1] if main_table.endswith('s') else main_table
    return f"{base_name}_readers"

def table_exists(cursor, table_name):
    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = %s
            );
        """, (table_name.lower(),))
        return cursor.fetchone()[0]
    except Exception as e:
        logger.error(f"Error checking table existence: {e}")
        return False

def get_entity_ids(cursor, main_table):
    try:
        cursor.execute(f"SELECT id FROM {main_table}")
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting entities from {main_table}: {e}")
        return []

def permission_exists(cursor, reader_table, user_id, entity_id):
    try:
        cursor.execute(f"""
            SELECT 1 FROM {reader_table} 
            WHERE reader = %s AND entity_id = %s
            LIMIT 1;
        """, (user_id, entity_id))
        return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking permissions: {e}")
        return False

def add_permissions(cursor, user_id, reader_table, main_table, is_superuser):
    try:
        if not table_exists(cursor, reader_table):
            logger.warning(f"Permission table {reader_table} does not exist")
            return 0

        entity_ids = get_entity_ids(cursor, main_table)
        if not entity_ids:
            logger.warning(f"No entities found in {main_table}")
            return 0

        permissions_added = 0
        can_edit = 1 if is_superuser else 0
        can_delete = 1 if is_superuser else 0

        for entity_id in entity_ids:
            if permission_exists(cursor, reader_table, user_id, entity_id):
                logger.debug(f"Permission exists for user {user_id} on {entity_id}")
                continue

            now = datetime.now()
            cursor.execute(f"""
                INSERT INTO {reader_table} 
                    (reader, entity_id, can_edit, can_delete, reading_time)
                VALUES (%s, %s, %s, %s, %s);
            """, (user_id, entity_id, can_edit, can_delete, now))
            permissions_added += 1
            access_type = "superuser" if is_superuser else "read-only"
            logger.info(f"Added {access_type} access for user {user_id} on {entity_id}")

        return permissions_added

    except Exception as e:
        logger.error(f"Failed to add permissions for user {user_id}: {e}")
        raise

def grant_access():
    if not MAIN_TABLES:
        logger.warning("No tables configured")
        return

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM _users WHERE i_su = TRUE")
        superusers = [row[0] for row in cursor.fetchall()]
        all_users = superusers + READ_ONLY_USER_IDS

        if not all_users:
            logger.info("No users to process")
            return

        logger.info(f"Processing {len(superusers)} superusers and {len(READ_ONLY_USER_IDS)} read-only users")
        total_permissions = 0

        for user_id in all_users:
            is_superuser = user_id in superusers
            for main_table in MAIN_TABLES:
                reader_table = get_reader_table_name(main_table)
                try:
                    added = add_permissions(cursor, user_id, reader_table, main_table, is_superuser)
                    total_permissions += added
                except Exception as e:
                    logger.error(f"Error processing {reader_table}: {e}")
                    conn.rollback()
                    continue

        conn.commit()
        logger.info(f"Completed: Added {total_permissions} permission records")

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
    grant_access()