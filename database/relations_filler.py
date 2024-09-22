from database import get_connection

def fill_user_modules_relations():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM _users")
    users = cursor.fetchall()

    cursor.execute("SELECT id FROM _modules")
    modules = cursor.fetchall()

    for user in users:
        for module in modules:
            cursor.execute("""
                INSERT INTO _user_modules (user_id, module_id)
                VALUES (%s, %s)
                """, (user[0], module[0]))

    conn.commit()
    cursor.close()
    conn.close()

def fill_user_roles_relations():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM _users")
    users = cursor.fetchall()

    cursor.execute("SELECT id FROM _roles")
    roles = cursor.fetchall()

    for user in users:
        for role in roles:
            cursor.execute("""
                INSERT INTO _user_roles (user_id, role_id)
                VALUES (%s, %s)
                """, (user[0], role[0]))

    conn.commit()
    cursor.close()
    conn.close()
