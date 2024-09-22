from faker import Faker
from database import get_connection
from util.logging import logger

fake = Faker()

def generate_users(count=10):
    conn = get_connection()
    cursor = conn.cursor()

    for i in range(count):
        try:
            cursor.execute("""
                INSERT INTO _users (author, last_mod_user, login, email, default_lang, status, reg_date, last_mod_date)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                0,  # author set to 0
                0,  # last_mod_user set to 0
                fake.user_name(),
                fake.email(),
                fake.random_int(min=1, max=5),  # default_lang can map to predefined languages
                fake.random_int(min=0, max=1),  # status (active/inactive)
            ))
            logger.info(f"User {i + 1}/{count} inserted.")
        except Exception as e:
            logger.error(f"Error inserting user {i + 1}: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting users.")
