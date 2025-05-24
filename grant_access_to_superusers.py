from datetime import datetime
from database import get_connection  # Assuming you have this module
from util.logging import logger  # Assuming you have this module
import uuid  # Assuming you have this module

TABLE_PROCESSING_CONFIG = [
    {"table": "kneobroadcaster__sound_fragments", "ids": ["11ef0bf3-ff5e-40b6-84d5-a861b0814e9e"]},
]

READ_ONLY_USER_IDS = [
    5, 6
]

CAN_EDIT_USER_IDS = [
    5, 6
]

CAN_DELETE_USER_IDS = [
    5, 6
]


def get_reader_table_name(main_table):
    base_name = main_table[:-1] if main_table.endswith('s') else main_table
    return f"{base_name}_readers"


def table_exists(cursor, table_name):
    """Checks if a table exists in the database."""
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


def get_permission_details(cursor, reader_table, principal_id, entity_id):
    """Fetches (can_edit, can_delete) for an existing permission, or None if not found."""
    try:
        cursor.execute(f"""
            SELECT can_edit, can_delete FROM {reader_table} 
            WHERE reader = %s AND entity_id = %s
            LIMIT 1;
        """, (principal_id, entity_id))
        row = cursor.fetchone()
        if row:
            return row[0], row[1]
        return None
    except Exception as e:
        logger.error(
            f"Error fetching permission details for principal {principal_id}, entity {entity_id} in {reader_table}: {e}")
        return None


def add_permissions(cursor, principal_id, reader_table, main_table_name,
                    can_edit_for_principal, can_delete_for_principal,
                    entity_ids_list_filter=None):
    """
    Adds or updates permissions for a principal to entities in a table.
    """
    try:
        if not table_exists(cursor, reader_table):
            logger.warning(
                f"Permission table {reader_table} does not exist. Skipping for principal {principal_id}, main table {main_table_name}.")
            return 0

        entity_ids_to_process = get_entity_ids(cursor, main_table_name, specific_entity_ids=entity_ids_list_filter)

        if not entity_ids_to_process:
            if entity_ids_list_filter and len(entity_ids_list_filter) > 0:
                logger.info(
                    f"Specified Entity IDs {entity_ids_list_filter} not found in {main_table_name} or no entities to process for these IDs.")
            elif not entity_ids_list_filter or len(entity_ids_list_filter) == 0:
                logger.info(
                    f"No entities found in {main_table_name} (or filter was empty/None, implying all, but table is empty).")
            return 0

        permissions_changed = 0
        now = datetime.now()

        for entity_id in entity_ids_to_process:
            existing_details = get_permission_details(cursor, reader_table, principal_id, entity_id)

            operation_performed = False
            if existing_details:
                existing_can_edit, existing_can_delete = existing_details
                if existing_can_edit != can_edit_for_principal or existing_can_delete != can_delete_for_principal:
                    logger.info(
                        f"Updating permission for principal {principal_id} on entity {entity_id} in {reader_table} "
                        f"from (edit:{existing_can_edit}, delete:{existing_can_delete}) "
                        f"to (edit:{can_edit_for_principal}, delete:{can_delete_for_principal}).")
                    try:
                        cursor.execute(f"""
                            UPDATE {reader_table}
                            SET can_edit = %s, can_delete = %s, reading_time = %s
                            WHERE reader = %s AND entity_id = %s;
                        """, (can_edit_for_principal, can_delete_for_principal, now, principal_id, entity_id))
                        permissions_changed += 1
                        operation_performed = True
                    except Exception as update_e:
                        logger.error(
                            f"Failed to update permission for principal {principal_id}, entity {entity_id} in {reader_table}: {update_e}")
                else:
                    logger.debug(
                        f"Permission already exists with correct flags for principal {principal_id} on entity {entity_id} in {reader_table}. No update needed.")
            else:
                logger.info(
                    f"No existing permission found for principal {principal_id} on entity {entity_id} in {reader_table}. Inserting new permission.")
                try:
                    cursor.execute(f"""
                        INSERT INTO {reader_table} 
                            (reader, entity_id, can_edit, can_delete, reading_time)
                        VALUES (%s, %s, %s, %s, %s);
                    """, (principal_id, entity_id, can_edit_for_principal, can_delete_for_principal, now))
                    permissions_changed += 1
                    operation_performed = True
                except Exception as insert_e:
                    logger.error(
                        f"Failed to insert permission for principal {principal_id}, entity {entity_id} into {reader_table}: {insert_e}")

            if operation_performed:
                access_parts = ["read"]
                if can_edit_for_principal:
                    access_parts.append("edit")
                if can_delete_for_principal:
                    access_parts.append("delete")
                access_type_str = "-".join(access_parts)
                logger.info(
                    f"Applied {access_type_str} access for principal {principal_id} to entity {entity_id} in {reader_table} (main table: {main_table_name}).")

        return permissions_changed

    except Exception as e:
        logger.error(
            f"General error in add_permissions for principal {principal_id}, main table {main_table_name}, reader table {reader_table}: {e}")
        raise


def grant_access():
    """
    Grants access permissions based on TABLE_PROCESSING_CONFIG and ID lists.
    """
    if not TABLE_PROCESSING_CONFIG:
        logger.warning("TABLE_PROCESSING_CONFIG is empty. No operations to perform.")
        return

    all_involved_ids = set()
    all_involved_ids.update(READ_ONLY_USER_IDS)
    all_involved_ids.update(CAN_EDIT_USER_IDS)
    all_involved_ids.update(CAN_DELETE_USER_IDS)

    unique_principal_ids = list(all_involved_ids)

    if not unique_principal_ids:
        logger.info("No principals defined in READ_ONLY_USER_IDS, CAN_EDIT_USER_IDS, or CAN_DELETE_USER_IDS.")
        return

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        logger.info(f"Processing permissions for {len(unique_principal_ids)} unique principal(s).")

        total_permissions_granted_session = 0

        for operation_config in TABLE_PROCESSING_CONFIG:
            table_name = operation_config.get("table")
            specific_ids_for_table = operation_config.get("ids", [])

            if not table_name:
                logger.warning(
                    f"Skipping invalid operation config: 'table' key missing or empty. Config: {operation_config}")
                continue

            logger.info(f"Processing configuration for table: '{table_name}'")
            if specific_ids_for_table and len(specific_ids_for_table) > 0:
                logger.info(f"Targeting specific entity IDs: {specific_ids_for_table}")
            else:
                logger.info(f"Targeting all entity IDs in this table (as 'ids' list is empty or not specified).")

            for principal_id in unique_principal_ids:
                can_edit = principal_id in CAN_EDIT_USER_IDS
                can_delete = principal_id in CAN_DELETE_USER_IDS

                current_reader_table_name = get_reader_table_name(table_name)
                logger.debug(
                    f"Determining permissions for principal {principal_id} on table '{table_name}'. Edit: {can_edit}, Delete: {can_delete}.")

                try:
                    added_or_updated_count = add_permissions(
                        cursor,
                        principal_id,
                        current_reader_table_name,
                        table_name,
                        can_edit,
                        can_delete,
                        entity_ids_list_filter=specific_ids_for_table
                    )
                    total_permissions_granted_session += added_or_updated_count
                except Exception as e:
                    logger.error(
                        f"Error occurred while processing permissions for principal {principal_id} on main table {table_name}: {e}")
                    if conn:
                        conn.rollback()
                    logger.info(
                        "Transaction rolled back due to error. Halting processing for current table config.")
                    break
            else:
                continue
            break

        if conn:
            conn.commit()
        logger.info(
            f"Permission processing completed. Total permission records inserted or updated in this session: {total_permissions_granted_session}")

    except Exception as e:
        logger.error(f"Grant access process failed critically: {e}")
        if conn:
            conn.rollback()
            logger.info("Transaction rolled back due to critical failure.")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        logger.info("Database connection closed.")


if __name__ == "__main__":
    logger.info("Starting permission granting script...")
    grant_access()
    logger.info("Permission granting script finished.")