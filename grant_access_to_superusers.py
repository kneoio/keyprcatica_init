from datetime import datetime
from database import get_connection
from util.logging import logger

#MAIN_TABLE = "kneobroadcaster__listeners"
#READER_TABLE = "kneobroadcaster__listener_readers"

READ_ONLY_USER_IDS = [1, 5, 6]
CAN_EDIT_USER_IDS = [1, 5, 6]
CAN_DELETE_USER_IDS = [1, 5, 6]

TARGET_ENTITY_IDS = []


def table_exists(cursor, table_name):
    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = %s
            );
        """, (table_name.lower(),))
        result = cursor.fetchone()
        return result[0] if result else False
    except Exception as e:
        logger.error(f"Error checking table existence for {table_name}: {e}")
        return False


def get_entity_ids(cursor):
    try:
        if TARGET_ENTITY_IDS:
            if len(TARGET_ENTITY_IDS) == 1:
                cursor.execute(f"SELECT id FROM {MAIN_TABLE} WHERE id = %s", (TARGET_ENTITY_IDS[0],))
            else:
                cursor.execute(f"SELECT id FROM {MAIN_TABLE} WHERE id IN %s", (tuple(TARGET_ENTITY_IDS),))
        else:
            cursor.execute(f"SELECT id FROM {MAIN_TABLE}")

        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting entity IDs from {MAIN_TABLE}: {e}")
        return []


def get_existing_permission(cursor, user_id, entity_id):
    try:
        cursor.execute(f"""
            SELECT can_edit, can_delete FROM {READER_TABLE} 
            WHERE reader = %s AND entity_id = %s
            LIMIT 1;
        """, (user_id, entity_id))
        row = cursor.fetchone()
        return row if row else None
    except Exception as e:
        logger.error(f"Error fetching existing permission for user {user_id}, entity {entity_id}: {e}")
        return None


def grant_permission(cursor, user_id, entity_id, can_edit, can_delete):
    try:
        now = datetime.now()
        existing = get_existing_permission(cursor, user_id, entity_id)

        if existing:
            existing_edit, existing_delete = existing
            if existing_edit != can_edit or existing_delete != can_delete:
                cursor.execute(f"""
                    UPDATE {READER_TABLE}
                    SET can_edit = %s, can_delete = %s, reading_time = %s
                    WHERE reader = %s AND entity_id = %s;
                """, (can_edit, can_delete, now, user_id, entity_id))
                logger.info(f"Updated permission for user {user_id} on entity {entity_id}")
                return True
            else:
                logger.debug(f"Permission already correct for user {user_id} on entity {entity_id}")
                return False
        else:
            cursor.execute(f"""
                INSERT INTO {READER_TABLE} 
                (reader, entity_id, can_edit, can_delete, reading_time)
                VALUES (%s, %s, %s, %s, %s);
            """, (user_id, entity_id, can_edit, can_delete, now))
            logger.info(f"Created new permission for user {user_id} on entity {entity_id}")
            return True

    except Exception as e:
        logger.error(f"Error granting permission for user {user_id}, entity {entity_id}: {e}")
        raise


def grant_access():
    """Main function to grant access permissions."""
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if reader table exists
        if not table_exists(cursor, READER_TABLE):
            logger.error(f"Reader table {READER_TABLE} does not exist!")
            return

        # Get all entity IDs to process
        entity_ids = get_entity_ids(cursor)
        if not entity_ids:
            logger.warning("No entities found to process")
            return

        logger.info(f"Processing {len(entity_ids)} entities for permissions")

        # Get all unique user IDs
        all_user_ids = set()
        all_user_ids.update(READ_ONLY_USER_IDS)
        all_user_ids.update(CAN_EDIT_USER_IDS)
        all_user_ids.update(CAN_DELETE_USER_IDS)

        total_changes = 0

        # Process each user
        for user_id in all_user_ids:
            can_edit = user_id in CAN_EDIT_USER_IDS
            can_delete = user_id in CAN_DELETE_USER_IDS

            logger.info(f"Processing user {user_id} - Edit: {can_edit}, Delete: {can_delete}")

            # Grant permission for each entity
            for entity_id in entity_ids:
                try:
                    if grant_permission(cursor, user_id, entity_id, can_edit, can_delete):
                        total_changes += 1
                except Exception as e:
                    logger.error(f"Failed to process user {user_id}, entity {entity_id}: {e}")
                    conn.rollback()
                    return

        # Commit all changes
        conn.commit()
        logger.info(f"Successfully granted access. Total changes: {total_changes}")

    except Exception as e:
        logger.error(f"Critical error in grant_access: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    logger.info("Starting permission granting for kneobroadcaster__listeners...")
    grant_access()
    logger.info("Permission granting completed.")