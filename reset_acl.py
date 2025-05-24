import os
from datetime import datetime
from dotenv import load_dotenv
from database import get_connection  # Assuming you have this module
from util.logging import logger  # Assuming you have this module
import uuid  # Assuming you have this module

load_dotenv()

TABLE_PROCESSING_CONFIG = [
    {"table": "kneobroadcaster__sound_fragments", "ids": []},
    # Example: {"table": "another_table", "ids": ["specific_uuid_1", "specific_uuid_2"]},
]

USER_TO_REVOKE = [
    # Add user/principal IDs here whose permissions should be revoked
    # Example: 5, "another_user_uuid"
]


def get_reader_table_name(main_table):
    base_name = main_table[:-1] if main_table.endswith('s') else main_table
    return f"{base_name}_readers"


def table_exists(cursor, table_name):
    """Checks if a table exists in the database."""
    try:
        cursor.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s);",
                       (table_name.lower(),))
        result = cursor.fetchone()
        return result[0] if result else False
    except Exception as e:
        logger.error(f"Error checking table existence for {table_name}: {e}")
        return False


def get_entity_ids(cursor, main_table, specific_entity_ids=None):
    """
    Fetches entity IDs from the main_table.
    An empty list or None for specific_entity_ids means fetch all.
    """
    try:
        query = ""
        params = ()
        if specific_entity_ids and isinstance(specific_entity_ids, list) and len(specific_entity_ids) > 0:
            if len(specific_entity_ids) == 1:
                query = f"SELECT id FROM {main_table} WHERE id = %s"
                params = (specific_entity_ids[0],)
            else:
                query = f"SELECT id FROM {main_table} WHERE id IN %s"
                params = (tuple(specific_entity_ids),)
            cursor.execute(query, params)
        else:
            query = f"SELECT id FROM {main_table}"
            cursor.execute(query)
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting entities from {main_table} (specific_ids: {specific_entity_ids}): {e}")
        return []


def revoke_specified_permissions():
    """
    Revokes permissions for users in USER_TO_REVOKE for entities specified in TABLE_PROCESSING_CONFIG.
    """
    if not TABLE_PROCESSING_CONFIG:
        logger.warning("TABLE_PROCESSING_CONFIG is empty. No revocation scope defined.")
        return
    if not USER_TO_REVOKE:
        logger.info("USER_TO_REVOKE list is empty. No users specified for permission revocation.")
        return

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        total_permissions_revoked_count = 0
        logger.info(f"Starting permission revocation process for {len(USER_TO_REVOKE)} specified principal(s).")

        for config_item in TABLE_PROCESSING_CONFIG:
            table_name = config_item.get("table")
            specified_entity_ids_for_config = config_item.get("ids", [])

            if not table_name:
                logger.warning(f"Skipping invalid configuration item (missing 'table' key): {config_item}")
                continue

            reader_table_name = get_reader_table_name(table_name)
            if not table_exists(cursor, reader_table_name):
                logger.warning(
                    f"Reader table '{reader_table_name}' for main table '{table_name}' does not exist. Skipping.")
                continue

            logger.info(f"Processing revocations for table '{table_name}'.")

            entity_ids_to_operate_on = []
            if specified_entity_ids_for_config and len(specified_entity_ids_for_config) > 0:
                entity_ids_to_operate_on = get_entity_ids(cursor, table_name,
                                                          specific_entity_ids=specified_entity_ids_for_config)
                if not entity_ids_to_operate_on:
                    logger.info(
                        f"No matching entities found for specified IDs {specified_entity_ids_for_config} in table '{table_name}'. Skipping this part of the config.")
                    continue
                if len(entity_ids_to_operate_on) != len(specified_entity_ids_for_config):
                    # This accounts for if some specified IDs were not found
                    logger.warning(
                        f"For table '{table_name}', some specified entity IDs were not found or were duplicates. "
                        f"Specified: {specified_entity_ids_for_config}, Effectively processing for: {entity_ids_to_operate_on}")
            else:
                entity_ids_to_operate_on = get_entity_ids(cursor, table_name, specific_entity_ids=None)
                logger.info(
                    f"Targeting all {len(entity_ids_to_operate_on)} entities in table '{table_name}' for revocation.")

            if not entity_ids_to_operate_on:
                logger.info(f"No actual entity IDs to process for revocation in table '{table_name}'.")
                continue

            for entity_id in entity_ids_to_operate_on:
                for user_id_to_revoke in USER_TO_REVOKE:
                    try:
                        logger.debug(
                            f"Attempting to revoke permission for user {user_id_to_revoke} on entity {entity_id} in {reader_table_name}.")
                        cursor.execute(f"""
                            DELETE FROM {reader_table_name}
                            WHERE reader = %s AND entity_id = %s;
                        """, (user_id_to_revoke, entity_id))

                        rows_deleted = cursor.rowcount
                        if rows_deleted > 0:
                            logger.info(
                                f"Revoked {rows_deleted} permission record(s) for user {user_id_to_revoke} on entity {entity_id} from {reader_table_name}.")
                            total_permissions_revoked_count += rows_deleted
                        else:
                            logger.debug(
                                f"No existing permission found to revoke for user {user_id_to_revoke} on entity {entity_id} in {reader_table_name}.")
                    except Exception as e_revoke:
                        logger.error(
                            f"Failed to revoke permission for user {user_id_to_revoke} on entity {entity_id} in {reader_table_name}: {e_revoke}")
                        if conn:
                            conn.rollback()
                        raise

        if conn:
            conn.commit()
        logger.info(
            f"Permission revocation process complete. {total_permissions_revoked_count} permission records were revoked in total.")

    except Exception as e:
        logger.error(f"Overall permission revocation process failed: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn and cursor:
            cursor.close()
        if conn:
            conn.close()
        logger.info("Database connection closed.")


if __name__ == "__main__":
    logger.info("Starting permission revocation script...")
    revoke_specified_permissions()
    logger.info("Permission revocation script finished.")