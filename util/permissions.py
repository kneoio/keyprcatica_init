from datetime import datetime

def add_superuser_permissions(cursor, entity_id, table_name):
    now = datetime.now()
    cursor.execute(f"""
        INSERT INTO {table_name} (reader, entity_id, can_edit, can_delete, reading_time)
        VALUES (%s, %s, %s, %s, %s)
    """, (1, entity_id, True, True, now))
