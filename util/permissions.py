from datetime import datetime

users = [1, 5, 6]


def add_default_superuser_permissions(cursor, entity_id, table_name):
    now = datetime.now()

    for user_id in users:
        cursor.execute(f"""
            INSERT INTO {table_name} (reader, entity_id, can_edit, can_delete, reading_time)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, entity_id, True, True, now))